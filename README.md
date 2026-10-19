# End-to-End Communication System Simulation over an ARINC 429 Link

Communication Theory, Practical 8 (Mini-Project)
Uganda Christian University, Department of Electronics, Communication and Computer Engineering

| Name | Registration number |
|---|---|
| Shiisa Jacob | S25B48/056 |
| Kasozi Nimusiima Erina | S25B48/046 |

**Language used: Python** (NumPy, SciPy, Matplotlib)

## What this project does

Simulates the full chain required by the practical:

Source → Sampling → Quantization/PCM → ARINC 429 framing → Bipolar RZ line code → BPSK modulation → AWGN channel → Coherent demodulation → ARINC 429 decoding and checks → PCM decoding → Reconstruction

A 300 Hz sensor signal is sampled at 8 kHz, quantized to 8 bits, packed into ARINC 429 words (two samples per word), line coded with the ARINC 429 bipolar return-to-zero code, and sent over a BPSK link through an AWGN channel. The report studies how channel SNR (Eb/N0) affects reconstruction MSE and links the results to Shannon's channel capacity theorem.

## How to run

1. Install Python 3.9 or later.
2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the project from the repository root:

   ```bash
   python main.py --quick   # whole chain, all figures, in a few seconds
   python main.py           # full Monte Carlo run (150 trials per Eb/N0 point)
   ```

All figures are saved to `figures/`. The sweep results are written to `figures/results.csv`.

## Repository structure

```
repo/
|-- main.py              entry point: runs the full chain
|-- functions/           one module per stage
|   |-- source.py        message signal generation
|   |-- pcm.py           quantizer and PCM encode/decode
|   |-- arinc429.py      ARINC 429 word framing and parsing
|   |-- line_coding.py   bipolar RZ line code
|   |-- modulation.py    BPSK modulation and coherent demodulation
|   |-- channel.py       AWGN channel (noise set by Eb/N0)
|   |-- reconstruction.py  concealment of rejected words, sinc reconstruction
|   |-- metrics.py       MSE and theory curves (BER, Shannon)
|   |-- plots.py         all figures
|   `-- system.py        wires the stages together, Monte Carlo sweep
|-- figures/             saved plots and results.csv
|-- report.ipynb         report notebook
|-- report.pdf           report
`-- README.md
```

## Report

The report is provided as `report.pdf` and as `report.ipynb`. It contains the block diagram, plots at every stage, the MSE against channel SNR analysis, and the discussion of Shannon's channel capacity theorem.

To run the notebook (from the repository root):

```bash
jupyter notebook report.ipynb
```

The notebook calls the same code in `functions/`, so its numbers match `main.py` (the Monte Carlo sweep uses a fixed seed, 2026).

## Notes

- ARINC 429 is a baseband bus with no carrier. To include a digital modulation stage, the bus data is modelled as relayed over a BPSK radio link, as in flight-test telemetry. The plain baseband bus is also run through the same channel for comparison.
- The practical's template uses `awgn(x, SNR, 'measured')`, which sets SNR per sample. This project sets noise by Eb/N0 instead. The two differ by a fixed offset for this waveform (SNR per sample = Eb/N0 − 13.52 dB), and both axes are shown in the MSE figure.
