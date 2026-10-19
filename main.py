"""End-to-end communication system simulation over an ARINC 429 link.

Entry point. Runs the full chain

  Source -> Sampling -> Quantization/PCM -> ARINC 429 framing -> Bipolar RZ
  line code -> BPSK modulation -> AWGN channel -> Coherent demodulation ->
  ARINC 429 decoding -> PCM decoding -> Reconstruction

saves a figure for every stage plus the performance sweeps to figures/,
and writes the sweep results to figures/results.csv.

Usage:
    python main.py --quick   # few seconds (10 Monte Carlo runs per point)
    python main.py           # full run (150 Monte Carlo runs per point)
"""
import argparse
import csv
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from functions import arinc429, channel, metrics, plots, system

OUT = "figures"
EBN0 = np.arange(-4, 15)                       # dB, sweep range
EBN0_BASEBAND = np.array([-4, -2, 0, 2, 4, 6, 8, 10])


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true", help="10 trials per point instead of 150")
    ap.add_argument("--trials", type=int, default=None, help="override trials per point")
    args = ap.parse_args()
    trials = args.trials or (10 if args.quick else 150)
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()

    # ---- transmit chain ----------------------------------------------------
    txs = system.build_transmitter()
    cfg = txs["cfg"]
    floor = system.quantization_floor(txs)
    print(f"Samples: {len(txs['message'])}, ARINC 429 words: {len(txs['words'])}, "
          f"data bits: {txs['n_data_bits']}")
    print(f"Quantization MSE = {floor:.3e}, SQNR = {metrics.sqnr_db(txs['message'], floor):.1f} dB "
          f"(rule 6.02n+1.76 = {6.02 * cfg.n_bits + 1.76:.1f} dB)")
    print(f"First ARINC word: {arinc429.word_to_hex(txs['words'][0])}")

    # ---- stage figures -----------------------------------------------------
    print("Saving stage figures:")
    save(plots.fig_block_diagram(), "01_block_diagram.png")
    save(plots.fig_original(txs["t"], txs["message"]), "02_original.png")
    save(plots.fig_sampled(txs["t"], txs["message"], cfg.fs), "03_sampled.png")
    save(plots.fig_quantized(txs["t"], txs["message"], txs["quantized"], txs["step"], cfg.n_bits),
         "04_quantized.png")
    save(plots.fig_word(txs["words"][0], txs["codes"][:2]), "05a_arinc_word.png")
    save(plots.fig_line_code(txs["baseband"], cfg.samples_per_bit, gap_bits=cfg.gap_bits),
         "05b_line_code.png")
    save(plots.fig_bpsk(txs["baseband"], txs["tx"], txs["words"].ravel(), cfg.samples_per_bit),
         "06_bpsk.png")

    r3 = system.run_link(txs, 3, np.random.default_rng(8))   # seed chosen to show a few errors
    print(f"At Eb/N0 = 3 dB: {r3['bit_errors']} of {r3['n_bits']} bit errors "
          f"(BER {r3['bit_errors'] / r3['n_bits']:.2e}, theory {float(metrics.ber_theory(3)):.2e})")
    save(plots.fig_received(txs["tx"], r3["rx"], 3, cfg.samples_per_bit), "07_received.png")
    save(plots.fig_demod(r3["statistics"][txs["is_data"]], txs["words"].ravel(), r3["bits"], 3),
         "08_demodulated.png")
    runs = [system.run_link(txs, e, np.random.default_rng(7)) for e in (12, 4)]
    save(plots.fig_reconstruction(txs, runs), "09_reconstructed.png")

    # ---- parity example (flip bits in a clean word) -------------------------
    w = txs["words"][2].copy()
    print("Parity example (word 2):")
    for flips in ([], [15], [15, 21]):
        bad = w.copy()
        for b in flips:
            bad[b - 1] ^= 1
        f = arinc429.parse_words(bad[None, :])
        print(f"  flip {flips or 'none'}: parity {'PASS' if f['parity_ok'][0] else 'FAIL'}, "
              f"codes {f['codes'][0].tolist()}")

    # ---- Monte Carlo sweeps ------------------------------------------------
    print(f"Monte Carlo sweep: {trials} runs per point ...")
    sw = system.sweep(txs, EBN0, trials=trials)
    sw_bb = system.sweep(txs, EBN0_BASEBAND, trials=trials, mode="baseband")
    n_samples = len(txs["tx"])
    save(plots.fig_ber_words(sw, sw_bb), "10_ber_and_word_checks.png")
    save(plots.fig_mse(sw, floor, txs["n_data_bits"], n_samples), "11_mse_vs_snr.png")
    save(plots.fig_shannon(sw, floor), "12_shannon.png")

    # ---- results.csv ---------------------------------------------------------
    path = os.path.join(OUT, "results.csv")
    with open(path, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["ebn0_db", "snr_per_sample_db", "ber", "ber_theory", "word_error_rate",
                     "reject_rate", "undetected_rate", "mse_raw", "mse_hold", "mse_interp"])
        for i, e in enumerate(sw["ebn0_db"]):
            wr.writerow([f"{e:g}",
                         f"{channel.snr_per_sample_db(e, txs['n_data_bits'], n_samples):.2f}",
                         f"{sw['ber'][i]:.3e}", f"{float(metrics.ber_theory(e)):.3e}",
                         f"{sw['wer'][i]:.3e}", f"{sw['reject_rate'][i]:.3e}",
                         f"{sw['undetected_rate'][i]:.3e}", f"{sw['mse_raw'][i]:.3e}",
                         f"{sw['mse_hold'][i]:.3e}", f"{sw['mse_interp'][i]:.3e}"])
    print(f"  saved {path}")

    # ---- summary -------------------------------------------------------------
    print(f"\n{'Eb/N0':>6} {'BER':>10} {'theory':>10} {'MSE raw':>10} {'MSE hold':>10} {'MSE interp':>11}")
    for i, e in enumerate(sw["ebn0_db"]):
        if e in (0, 2, 4, 6, 8, 10, 12):
            print(f"{e:6g} {sw['ber'][i]:10.2e} {float(metrics.ber_theory(e)):10.2e} "
                  f"{sw['mse_raw'][i]:10.2e} {sw['mse_hold'][i]:10.2e} {sw['mse_interp'][i]:11.2e}")
    print(f"\nShannon limit for B = 4Rb: {metrics.shannon_min_ebn0_db(0.25):.2f} dB")
    print(f"Done in {time.time() - t0:.1f} s. Figures are in '{OUT}/'.")


if __name__ == "__main__":
    main()
