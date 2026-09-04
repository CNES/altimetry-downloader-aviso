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

The command line interface provides four main commands and one auxiliary command:

1. **summary** to list available products in the catalog;
2. **details** to view detailed metadata for a specific product;
3. **get** to download a given product applying filters, and the associated auxiliary command **help-query** for configuring said filters.
4. **subset** to download part of a given product applying filters, and the associated auxiliary command **help-query** for configuring said filters.

.. tip::

    - Use ``--help`` with any command to see available options.
    - Use ``--verbose`` or ``--quiet`` options to adjust logging verbosity.


.. _cli_summary:

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
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃ Short Name                    ┃ Title                                                                                                          ┃
    ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
    │ L4_with_SWOT                  │ Experimental Products: Multimission Gridded (with SWOT, MIOST only) Level-4 Sea Surface Heights and Velocities │
    │ SWOT_L2_LR_SSH_Basic          │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - Basic                                                      │
    │ SWOT_L2_LR_SSH_Expert         │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - Expert                                                     │
    │ SWOT_L2_LR_SSH_Unsmoothed     │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - Unsmoothed                                                 │
    │ SWOT_L2_LR_SSH_WindWave       │ Altimetry product SWOT Level-2 KaRIn Low Rate SSH - WindWave                                                   │
    │ SWOT_L3_LR_SSH_Basic          │ Altimetry product SWOT Level-3 Low Rate SSH - Basic                                                            │
    │ SWOT_L3_LR_SSH_Expert         │ Altimetry product SWOT Level-3 Low Rate SSH - Expert                                                           │
    │ SWOT_L3_LR_SSH_Technical      │ Altimetry product SWOT Level-3 Low Rate SSH - Technical                                                        │
    │ SWOT_L3_LR_SSH_Unsmoothed     │ Altimetry product SWOT Level-3 Low Rate SSH - Unsmoothed                                                       │
    │ SWOT_L3_LR_WIND_WAVE_Extended │ Wind & Wave product SWOT Level-3 WindWave - Extended                                                           │
    │ SWOT_L3_LR_WIND_WAVE_Light    │ Wind & Wave product SWOT Level-3 WindWave - Light                                                              │
    └───────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

.. _cli_details:

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
    │ │ Last Update               │ 2025-11-26 23:00:00+00:00                                                                                                                                                                                                                                                        │ │
    │ │ Last Version              │ v3.0                                                                                                                                                                                                                                                                             │ │
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

   altimetry-downloader-aviso get <product_short_name> --output <directory> [--cycle <comma separated values/ranges>>] [--pass <comma separated values/ranges>] [--start <YYYY-MM-DD>] [--end <YYYY-MM-DD>] [--version <product version>] [--box <box>]

.. _cli_help_query:

**List filter values**

Before downloading data with the ``get`` command, a dedicated ``help-query`` command lists the temporal coverage, half orbit range (if relevant)
and versions of a product. When dealing with a product that follows a satellite orbit, the information is displayed for each phase of the mission.
This information can be used to configure the ``get`` command arguments filtering the granules.

.. code-block:: console

    $ altimetry-downloader-aviso help-query SWOT_L3_LR_SSH_Basic
                                                    Dataset Information
    ┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
    ┃ Phase   ┃ Property          ┃ Value                                                    ┃ get parameters  ┃
    ┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
    │ CALVAL  │ Temporal Coverage │ [2023-03-28T23:44:17.000000, 2023-07-10T09:12:05.000000] │ --start, --end  │
    │         │ Half Orbit Range  │ ((474, 3), (578, 4))                                     │ --cycle, --pass │
    ├─────────┼───────────────────┼──────────────────────────────────────────────────────────┼─────────────────┤
    │ SCIENCE │ Temporal Coverage │ [2023-07-26T12:27:56.000000, 2026-08-31T20:30:51.000000] │ --start, --end  │
    │         │ Half Orbit Range  │ ((1, 149), (55, 306))                                    │ --cycle, --pass │
    ├─────────┼───────────────────┼──────────────────────────────────────────────────────────┼─────────────────┤
    │ All     │ Versions          │ 2.0.1, 3.0                                               │ --version       │
    └─────────┴───────────────────┴──────────────────────────────────────────────────────────┴─────────────────┘

.. _cli_get:

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

This command downloads Swot LR L3 Basic, in the period from 2025-01-01 to 2025-01-02, and stores the requested files to /aviso_dir.

.. code-block:: console

    $ altimetry-downloader-aviso get SWOT_L3_LR_SSH_Basic --output aviso_dir --start 2025-01-01 --end 2025-01-02
    Local files (29) :
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_229_20241231T235043_20250101T004209_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_230_20250101T004210_20250101T013336_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_231_20250101T013336_20250101T022503_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_232_20250101T022504_20250101T031630_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_233_20250101T031630_20250101T040757_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_234_20250101T040757_20250101T045923_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_235_20250101T045924_20250101T055051_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_236_20250101T055051_20250101T064217_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_237_20250101T064217_20250101T073344_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_238_20250101T073344_20250101T082510_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_239_20250101T082511_20250101T091637_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_240_20250101T091638_20250101T100804_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_241_20250101T100805_20250101T105931_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_242_20250101T105932_20250101T115058_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_243_20250101T115058_20250101T124225_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_244_20250101T124225_20250101T133351_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_245_20250101T133352_20250101T142518_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_246_20250101T142519_20250101T151645_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_247_20250101T151646_20250101T160812_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_248_20250101T160813_20250101T165939_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_249_20250101T165939_20250101T175106_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_250_20250101T175106_20250101T184232_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_251_20250101T184233_20250101T193359_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_252_20250101T193400_20250101T202526_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_253_20250101T202527_20250101T211653_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_254_20250101T211653_20250101T220820_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_255_20250101T220820_20250101T225946_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_256_20250101T225947_20250101T235114_v3.0.nc
    - aviso_dir/SWOT_L3_LR_SSH_Basic_026_257_20250101T235114_20250102T004240_v3.0.nc


.. note::

    Requests with ``start`` / ``--end`` filters call the `Altimetry Search <https://github.com/CNES/altimetry-search>`_ tool to find the cycles matching the requested time range.
    The ``--cycle`` filter is then applied to the list of granules returned by the search tool. This considerably accelerates the granules selection process.

**Example with version filter:**

By default, the latest version of the product is downloaded. Use ``--version`` option to specify a different version.

This command downloads Swot LR L3 Basic, cycle number 7, half-orbit 12, version 2.0.1, and stores the requested files to /aviso_dir.

.. code-block:: console

    $ altimetry-downloader-aviso get SWOT_L3_LR_SSH_Basic --output aviso_dir --cycle 7 --pass 12 --version 2.0.1
    Local files (1) :
    - aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v2.0.1.nc

**Example with box filter:**

Use ``--box``  option to download files representing passes that fall within the specified bounding box.

.. caution::

    Since unsmoothed products are very large, it is recommended to use the ``subset`` command with filters to reduce the amount of data loaded, instead of downloading the entire passes with the ``get`` command.

This command downloads Swot LR L3 Unsmoothed passes that cross the specified bounding box (lon_min, lat_min, lon_max, lat_max)=(-10,10,10,40), and stores the requested files to /aviso_dir.

.. code-block:: console

    $ altimetry-downloader-aviso get SWOT_L3_LR_SSH_Unsmoothed --output aviso_dir --box -10,10,10,40  --cycle 1 --pass 154,169,236,401
    Local files (2) :
    - aviso_dir/SWOT_L3_LR_SSH_Unsmoothed_001_169_20230727T053653_20230727T062820_v2.0.1.nc
    - aviso_dir/SWOT_L3_LR_SSH_Unsmoothed_001_154_20230726T164516_20230726T173637_v2.0.1.nc

.. caution::

    If no ``--start``, ``--end`` nor ``--cycle`` aren't provided in the request, the command will download all the passes that cross the specified bounding box. This can result in a large number of files being downloaded.

    Furthermore, the requested phase cannot be determined without a ``--start``, ``--end`` or ``--cycle`` filter, so the `Science` phase is selected by default.

    Therefore, it is recommended to use the ``--start``, ``--end`` or ``--cycle`` options to limit the time range of the request, and determine the phase of the mission.

.. note::

    `Altimetry Search <https://github.com/CNES/altimetry-search>`_ tool is called to find the passes that cross the bounding box.
    If passes are selected with the ``--pass`` option, it narrows the candidate passes tested against the bounding box. If a pass does not cross the bounding box, it will not be downloaded.

.. _cli_subset:

Subset a product
~~~~~~~~~~~~~~~~

The ``subset`` command can select a part of a given AVISO product. It can be
parametrized with:

* An area of interest: ``--box/-b`` parameter given as (lon_min, lat_min, lon_max, lat_max),
  with the longitudes in any convention, and lon_min < lon_max
* A subset of variables: ``--variables/-x`` parameter


**Usage:**

.. code-block:: bash

   altimetry-downloader-aviso subset <product_short_name> --output <directory> [--cycle <comma separated values/ranges>>] [--pass <comma separated values/ranges>] [--start <YYYY-MM-DD>] [--end <YYYY-MM-DD>] [--version <product version>] [--variables <selected variables>] [--box <box>]

The filters used in the ``get`` command (cycle, pass, start, end, version, box) should also
be used to find the granules prior the subsetting. If a granule does not contain any
data in the area of interest, it will not be downloaded.

.. note::

    Subsetting is not implemented yet for the following products:
        * L4_with_SWOT
        * SWOT_L3_LR_WIND_WAVE_Light
        * SWOT_L3_LR_WIND_WAVE_Extended
        * SWOT_L2_LR_SSH_Unsmoothed

**Example**

.. code-block:: console

    $ altimetry-downloader-aviso subset SWOT_L3_LR_SSH_Unsmoothed --box -10,10,10,40 --variables ssha_unfiltered,time --cycle 1 --pass 223,225,236 -o aviso_dir --version 2.0.1
    Local files (1) :
    - aviso_dir/SWOT_L3_LR_SSH_Unsmoothed_001_223_20230729T035501_20230729T044628_v2.0.1.nc


.. caution::

    If no ``--start``, ``--end`` nor ``--cycle`` aren't provided in the request, the command will load all the passes that cross the specified bounding box. This can result in a large number of data being loaded.

    Furthermore, the desired phase cannot be determined without a ``--start``, ``--end`` or ``--cycle`` filter, so the `Science` phase is selected by default.

    Therefore, it is recommended to use the ``--start``, ``--end`` or ``--cycle`` options to limit the time range of the request, and determine the phase of the mission.

.. note::

    `Altimetry Search <https://github.com/CNES/altimetry-search>`_ tool is called to find the passes that cross the bounding box.
    If passes are selected with the ``--pass`` option, it narrows the candidate passes tested against the bounding box. If a pass does not cross the bounding box, it will not be downloaded.

Further Reading
----------------

- :doc:`../basic_usage/advanced_usage`
