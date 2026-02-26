# Altimetry Downloader Aviso

A tool to easily search and download altimetry products from the Aviso catalog.

- List products available and retrieve their metadata information
- Apply filters to download files in their original NetCDF format, via Aviso's Thredds Data Server using HTTPS connection.
- Both a command line interface and a Python interface


## Quick start

```bash
conda install -c conda-forge altimetry-downloader-aviso
```

## Use


### List products available in Aviso's catalog

For now, the tool only allows users to browse and download SWOT products.

```python

>>> altimetry-downloader-aviso summary

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Short Name                    ┃ Title                                                                                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ L4_exp_with_SWOT              │ Experimental Products: Multimission Gridded (with SWOT) Level-4 Sea Surface Heights and Velocities │
│ SWOT_L2_LR_SSH_Basic          │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - Basic                                          │
│ SWOT_L2_LR_SSH_Expert         │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - Expert                                         │
│ SWOT_L2_LR_SSH_Unsmoothed     │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - Unsmoothed                                     │
│ SWOT_L2_LR_SSH_WindWave       │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - WindWave                                       │
│ SWOT_L3_LR_SSH_Basic          │ Altimetry product SWOT Level-3 Low Rate SSH - Basic                                                │
│ SWOT_L3_LR_SSH_Expert         │ Altimetry product SWOT Level-3 Low Rate SSH - Expert                                               │
│ SWOT_L3_LR_SSH_Unsmoothed     │ Altimetry product SWOT Level-3 Low Rate SSH - Unsmoothed                                           │
│ SWOT_L3_LR_WIND_WAVE_Extended │ Wind & Wave product SWOT Level-3 WindWave - Extended                                               │
│ SWOT_L3_LR_WIND_WAVE_Light    │ Wind & Wave product SWOT Level-3 WindWave - Light                                                  │
└───────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┘

```

### Get a product details

```python

>>> altimetry-downloader-aviso details SWOT_L3_LR_SSH_Basic

╭───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── Product: SWOT_L3_LR_SSH_Basic ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ Field                     ┃ Value                                                                                                                                                                                                                                                                            ┃ │
│ ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩ │
│ │ Id                        │ aa2927ad-d1d6-4867-89d3-1311bc11e6bb                                                                                                                                                                                                                                             │ │
│ │ Title                     │ Altimetry product SWOT Level-3 Low Rate SSH - Basic                                                                                                                                                                                                                              │ │
│ │ Short Name                │ SWOT_L3_LR_SSH_Basic                                                                                                                                                                                                                                                             │ │
│ │ Keywords                  │ Platform(s): SWOT, SWOT                                                                                                                                                                                                                                                          │ │
│ │                           │ Instrument(s): POSEIDON-3C, KaRIn                                                                                                                                                                                                                                                │ │
│ │                           │ Parameters(s): Sea Surface Topography                                                                                                                                                                                                                                            │ │
│ │                           │ Spatial resolution: 2 km                                                                                                                                                                                                                                                         │ │
│ │                           │                                                                                                                                                                                                                                                                                  │ │
│ │ Abstract                  │ The SWOT L3_LR_SSH product provides ocean topography measurements obtained from the SWOT KaRIn and nadir altimeter instruments, merged into a single variable. The dataset includes measurements from KaRIn swaths on both sides of the image, while the measurements from the   │ │
│ │                           │ nadir altimeter are located in the central columns. In the areas between the nadir track and the two KaRIn swaths, as well as on the outer edges of each swath (restricted to cross-track distances ranging from 10 to 60 km), default values are expected.                      │ │
│ │                           │                                                                                                                                                                                                                                                                                  │ │
│ │                           │ SWOT L3_LR_SSH is a cross-calibrated product from multiple missions that contains only the ocean topography content necessary for thematic research (e.g., oceanography, geodesy) and related applications. This product is designed to be simple and ready-to-use, and can be   │ │
│ │                           │ combined with other altimetry missions.  The SWOT L3_LR_SSH product is a research-orientated extension of the L2_LR_SSH product, distributed by the SWOT project (NASA/JPL and CNES) and managed by the SWOT Science Team project DESMOS.                                        │ │
│ │                           │                                                                                                                                                                                                                                                                                  │ │
│ │                           │ The "Basic" version of SWOT L3_LR_SSH (the "Expert" version is the subject of a separate metadata sheet) includes only the SSH anomalies and mean dynamic topography.                                                                                                            │ │
│ │ Level                     │ L3                                                                                                                                                                                                                                                                               │ │
│ │ URL                       │ https://tds%40odatis-ocean.fr:odatis@tds-odatis.aviso.altimetry.fr/thredds/catalog/L3/SWOT_KARIN-L3_LR_SSH.html                                                                                                                                                                  │ │
│ │ DOI                       │ https://doi.org/10.24400/527896/A01-2023.017                                                                                                                                                                                                                                     │ │
│ │ Last Update               │ 2025-03-14 23:00:00+00:00                                                                                                                                                                                                                                                        │ │
│ │ Last Version              │ v3.0                                                                                                                                                                                                                                                                           │ │
│ │ Credit                    │ CDS-AVISO                                                                                                                                                                                                                                                                        │ │
│ │ Organisation              │ AVISO                                                                                                                                                                                                                                                                            │ │
│ │ Contact                   │ aviso@altimetry.fr                                                                                                                                                                                                                                                               │ │
│ │ Resolution                │ 2 km                                                                                                                                                                                                                                                                             │ │
│ │ Temporal extent           │ 2023-03-29 00:00:00, None                                                                                                                                                                                                                                                        │ │
│ │ Geographic extent         │ -180.0, 180.0, -80.0, 80.0                                                                                                                                                                                                                                                       │ │
│ └───────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```


### Download a product

```python

>>> altimetry-downloader-aviso get SWOT_L3_LR_SSH_Basic --output aviso_dir --cycle 7 --pass 12,13

Downloaded files (2) :
- aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc
- aviso_dir/SWOT_L3_LR_SSH_Basic_007_013_20231123T202138_20231123T211304_v3.0.nc

```

## Documentation

📘 **Full documentation:**
https://cnes.github.io/altimetry-downloader-aviso/index.html#

Key pages:
- [Installation](https://cnes.github.io/altimetry-downloader-aviso/getting_started/installation.html)
- [Command line interface](https://cnes.github.io/altimetry-downloader-aviso/getting_started/command_line_interface.html)
- [Python interface](https://cnes.github.io/altimetry-downloader-aviso/getting_started/python_interface.html)
- [Changelog](https://cnes.github.io/altimetry-downloader-aviso/changelog.html)


## License

Apache 2.0 — see [LICENSE](LICENSE)
