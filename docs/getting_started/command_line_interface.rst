Command Line Interface
======================

The ``altimetry-downloader-aviso`` command line interface allows you to interact easily with the Aviso catalog
to explore, inspect and download products.

After installation, the ``altimetry-downloader-aviso`` command becomes available in your terminal.

.. code-block:: bash

    altimetry-downloader-aviso --help

.. note::

    This CLI relies on the Python Interface operations. Please refer to :doc:`python_interface` for more information about these operations.


Available Commands
------------------

The command line interface provides three main commands:

1. **summary** to list available products in the catalog;
2. **details** to view detailed metadata for a specific product;
3. **get** to download a given product applying filters.

.. tip::

    - Use ``--help`` with any command to see available options.
    - Use ``--verbose`` or ``--quiet`` options to adjust logging verbosity.


List available products
~~~~~~~~~~~~~~~~~~~~~~~

Display a summary of the available Aviso products in the catalog using ``summary`` command.

**Usage:**

.. code-block:: bash

    altimetry-downloader-aviso summary

This will print a concise overview of the products (short names and titles).

**Example:**

.. code-block:: console

    $ altimetry-downloader-aviso summary
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
    │ SWOT_L3_LR_SSH_Technical      │ Altimetry product SWOT Level-3 Low Rate SSH - Technical                                            │
    │ SWOT_L3_LR_SSH_Unsmoothed     │ Altimetry product SWOT Level-3 Low Rate SSH - Unsmoothed                                           │
    │ SWOT_L3_LR_WIND_WAVE_Extended │ Wind & Wave product SWOT Level-3 WindWave - Extended                                               │
    │ SWOT_L3_LR_WIND_WAVE_Light    │ Wind & Wave product SWOT Level-3 WindWave - Light                                                  │
    └───────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┘


View product details
~~~~~~~~~~~~~~~~~~~~

Retrieve detailed metadata for a specific Aviso product using ``details`` command.

**Usage:**

.. code-block:: bash

    altimetry-downloader-aviso details <product_short_name>

**Example:**

.. code-block:: console

    $ altimetry-downloader-aviso details SWOT_L3_LR_SSH_Basic
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
    │ │ Last Update               │ 2025-11-26 23:00:00+00:00                                                                                                                                                                                                                                                  │ │
    │ │ Last Version              │ v3.0                                                                                                                                                                                                                                                                           │ │
    │ │ Credit                    │ CDS-AVISO                                                                                                                                                                                                                                                                        │ │
    │ │ Organisation              │ AVISO                                                                                                                                                                                                                                                                            │ │
    │ │ Contact                   │ aviso@altimetry.fr                                                                                                                                                                                                                                                               │ │
    │ │ Resolution                │ 2 km                                                                                                                                                                                                                                                                             │ │
    │ │ Temporal extent           │ 2023-03-29 00:00:00, None                                                                                                                                                                                                                                                        │ │
    │ │ Geographic extent         │ -180.0, 180.0, -80.0, 80.0                                                                                                                                                                                                                                                       │ │
    │ └───────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
    ╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Download a product
~~~~~~~~~~~~~~~~~~

Download a given Aviso product using ``get`` command.

**Usage:**

.. code-block:: bash

   altimetry-downloader-aviso get <product_short_name> --output <directory> [--cycle <comma separated values/ranges>>] [--pass <comma separated values/ranges>] [--start <YYYY-MM-DD>] [--end <YYYY-MM-DD>] [--version <product version>]

**Example cycle/pass filter:**

Use ``--cycle`` and ``--pass`` options to select mission cycle(s) and half-orbit(s) number(s).

This command downloads Swot LR L3 Basic, cycle number 7, half-orbits 12-13, and stores the requested files to /aviso_dir.

.. code-block:: console

    $ altimetry-downloader-aviso get SWOT_L3_LR_SSH_Basic --output aviso_dir --cycle 7 --pass 12,13
    Downloaded files (2) :
    - aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_007_013_20231123T202138_20231123T211304_v3.0.nc

.. note::

    You can provide multiple values/ranges for ``--cycle`` and ``--pass`` options, separated by commas (e.g., ``--cycle 5,7-9,12``).

**Example with time filter:**

Use ``--start`` and ``--end`` options to filter files by date range.

This command downloads Swot LR L3 Basic, in the period from 2025-01-01 to 2025-01-02, cycle number 26, and stores the requested files to /aviso_dir.

.. code-block:: console

    $ altimetry-downloader-aviso get SWOT_L3_LR_SSH_Basic --output aviso_dir --start 2025-01-01 --end 2025-01-02 --cycle 26
    Downloaded files (2) :
    - aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_007_013_20231123T202138_20231123T211304_v3.0.nc


.. caution::

    A request with only ``start`` / ``--end`` filters will take more time to compute, since it needs to browse all files to find ones included in the date range. Please provide a ``--cycle`` filter when possible.

**Example with version filter:**

By default, the latest version of the product is downloaded. Use ``--version`` option to specify a different version.

This command downloads Swot LR L3 Basic, cycle number 7, half-orbit 12, version 1.0.2, and stores the requested files to /aviso_dir.

.. code-block:: console

    $ altimetry-downloader-aviso get SWOT_L3_LR_SSH_Basic --output aviso_dir --cycle 7 --pass 12 --version 1.0.2
    Downloaded files (1) :
    - aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v1.0.2.nc


Further Reading
----------------

- :doc:`../basic_usage/advanced_usage`
