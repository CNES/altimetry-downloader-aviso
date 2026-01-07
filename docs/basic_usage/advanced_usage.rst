Advanced Usage
==============

Here are more detailed examples of how to use the Python Interface of the ``altimetry_downloader_aviso`` package.

Download Usage
--------------

Download a product using :func:`altimetry_downloader_aviso.get()` function.
For now, only cycle/pass, time and version filters are implemented.

.. code-block:: python

    from altimetry_downloader_aviso import get

Cycle / Pass filters
~~~~~~~~~~~~~~~~~~~~

``cycle_number`` and ``pass_number`` filters refer to mission cycle and half-orbit numbers. Multiple values can be provided as lists.

.. code-block:: pycon

    >>> local_files = get("SWOT_L3_LR_SSH_Basic", output_dir="aviso_dir", cycle_number=[7,8], pass_number=[12, 13])
    INFO:altimetry_downloader_aviso.catalog_client.client:Fetching products from Aviso's catalog...
    INFO:altimetry_downloader_aviso.catalog_client.granule_discoverer:Filtering SWOT_L3_LR_SSH_Basic product with filters {'cycle_number': [7, 8], 'pass_number': [12, 13]}...
    INFO:altimetry_downloader_aviso.core:4 files to download.
    INFO:altimetry_downloader_aviso.tds_client:File aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc downloaded.
    INFO:altimetry_downloader_aviso.tds_client:File aviso_dir/SWOT_L3_LR_SSH_Basic_007_013_20231123T202138_20231123T211304_v3.0.nc downloaded.
    INFO:altimetry_downloader_aviso.tds_client:File aviso_dir/SWOT_L3_LR_SSH_Basic_008_012_20231214T161515_20231214T170641_v3.0.nc downloaded.
    INFO:altimetry_downloader_aviso.tds_client:File aviso_dir/SWOT_L3_LR_SSH_Basic_008_013_20231214T170641_20231214T175808_v3.0.nc downloaded.
    >>> print(local_files)
    ['aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc',
     'aviso_dir/SWOT_L3_LR_SSH_Basic_007_013_20231123T202138_20231123T211304_v3.0.nc',
     'aviso_dir/SWOT_L3_LR_SSH_Basic_008_012_20231214T161515_20231214T170641_v3.0.nc',
     'aviso_dir/SWOT_L3_LR_SSH_Basic_008_013_20231214T170641_20231214T175808_v3.0.nc']



Temporal filters
~~~~~~~~~~~~~~~~

``time`` filter allows to specify a date range for the files to download. It should be provided as a tuple of two strings in "YYYY-MM-DD" format.

.. caution::

    A request with only ``time`` filter will take more time to compute, since it needs to browse all files to find ones included in the date range. Please provide a ``cycle_number`` filter when possible.


.. code-block:: pycon

    >>> local_files = get("SWOT_L3_LR_SSH_Basic", output_dir="aviso_dir", cycle_number=26, time=("2025-01-01", "2025-01-02"))

Version filter
~~~~~~~~~~~~~~

``version`` filter allows to specify the product version to download. By default, the latest version is downloaded.

.. code-block:: pycon

    >>> local_files = get("SWOT_L3_LR_SSH_Basic", output_dir="aviso_dir", cycle_number=7, pass_number=12, version='1.0.2')
    INFO:altimetry_downloader_aviso.catalog_client.client:Fetching products from Aviso's catalog...
    INFO:altimetry_downloader_aviso.catalog_client.granule_discoverer:Filtering SWOT_L3_LR_SSH_Basic product with filters {'cycle_number': 7, 'pass_number': 12, 'version': '1.0.2'}...
    INFO:altimetry_downloader_aviso.core:1 files to download. 0 files already exist.
    INFO:altimetry_downloader_aviso.tds_client:File aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v1.0.2.nc downloaded.
    >>> print(local_files)
    ['aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v1.0.2.nc']


Overwrite option
~~~~~~~~~~~~~~~~

By default, already existing files are not re-downloaded. Use ``overwrite=True`` parameter to force re-download.

.. code-block:: pycon

    >>> local_files = get("SWOT_L3_LR_SSH_Basic", output_dir="aviso_dir", cycle_number=7, pass_number=12)
    INFO:altimetry_downloader_aviso.catalog_client.client:Fetching products from Aviso's catalog...
    INFO:altimetry_downloader_aviso.catalog_client.granule_discoverer:Filtering SWOT_L3_LR_SSH_Basic product with filters {'cycle_number': 7, 'pass_number': 12}...
    INFO:altimetry_downloader_aviso.core:0 files to download. 1 files already exist.
    >>> print(local_files)
    ['aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc']

.. code-block:: pycon

    >>> local_files = get("SWOT_L3_LR_SSH_Basic", output_dir="aviso_dir", cycle_number=7, pass_number=12, overwrite=True)
    INFO:altimetry_downloader_aviso.catalog_client.client:Fetching products from Aviso's catalog...
    INFO:altimetry_downloader_aviso.catalog_client.granule_discoverer:Filtering SWOT_L3_LR_SSH_Basic product with filters {'cycle_number': 7, 'pass_number': 12}...
    INFO:altimetry_downloader_aviso.core:1 files to download.
    INFO:altimetry_downloader_aviso.tds_client:File aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc downloaded.
    >>> print(local_files)
    ['aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc']
