Python Interface
================

The ``altimetry_downloader_aviso`` tool provides a simple Python API to programmatically interact
with the Aviso catalog.

It exposes the Python functions equivalent to the CLI

+------------------------------------+---------------------------------------------------+
| Command Line Interface             | Python Function                                   |
+====================================+===================================================+
| :ref:`summary <cli_summary>`       | :func:`altimetry_downloader_aviso.summary()`      |
+------------------------------------+---------------------------------------------------+
| :ref:`details <cli_details>`       | :func:`altimetry_downloader_aviso.details()`      |
+------------------------------------+---------------------------------------------------+
| :ref:`help-query <cli_help_query>` | :func:`altimetry_downloader_aviso.filter_infos()` |
+------------------------------------+---------------------------------------------------+
| :ref:`get <cli_get>`               | :func:`altimetry_downloader_aviso.get()`          |
+------------------------------------+---------------------------------------------------+
| :ref:`subset <cli_subset>`         | :func:`altimetry_downloader_aviso.subset()`       |
+------------------------------------+---------------------------------------------------+


.. code-block:: python

    from altimetry_downloader_aviso import summary, details, get, get_product_from_short_name, filter_infos, subset

Basic Usage
-----------

List available products
~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a summary of the available products in Aviso catalog using :func:`altimetry_downloader_aviso.summary()` function. Retrieve an :class:`altimetry_downloader_aviso.AvisoCatalog` object.

.. code-block:: pycon

    >>> catalog = summary()
    >>> catalog
    AvisoCatalog(products=[AvisoProduct(id='d1f06620-d11c-4945-b53d-6769e909be01', title='Wind & Wave product SWOT Level-3 WindWave - Extended'), ...])

To list available products in the catalog, use the :attr:`altimetry_downloader_aviso.AvisoCatalog.products` attribute, that is a list of :class:`altimetry_downloader_aviso.AvisoProduct` objects.

.. code-block:: pycon

    >>> for product in catalog.products:
    >>>     print(f"{product.id}  {product.title}")
    SWOT_L3_LR_WIND_WAVE_Extended  Wind & Wave product SWOT Level-3 WindWave - Extended
    SWOT_L3_LR_SSH_Basic  Altimetry product SWOT Level-3 Low Rate SSH - Basic
    ...


View product details
~~~~~~~~~~~~~~~~~~~~

Get detailed metadata for a given product using :func:`altimetry_downloader_aviso.details()` function. It returns an :class:`altimetry_downloader_aviso.AvisoProduct` object.

.. code-block:: pycon

    >>> product = altimetry_downloader_aviso.details("SWOT_L3_LR_SSH_Basic")
    >>> print(product.abstract)
    The SWOT L3_LR_SSH product provides ocean topography measurements obtained from the SWOT KaRIn and nadir altimeter instruments,...


Download a product
~~~~~~~~~~~~~~~~~~

Download a product using :func:`altimetry_downloader_aviso.get()` function.

.. code-block:: pycon

    >>> local_files = get("SWOT_L3_LR_SSH_Basic", output_dir="aviso_dir", cycle_number=7, pass_number=[12, 13])
    >>> print(local_files)
    ['aviso_dir/SWOT_L3_LR_SSH_Basic_007_012_20231123T193011_20231123T202137_v3.0.nc',
     'aviso_dir/SWOT_L3_LR_SSH_Basic_007_013_20231123T202138_20231123T211304_v3.0.nc']

.. caution::

    By default, already existing files are not re-downloaded. Use ``--overwrite`` option to force re-download.

List filter values
~~~~~~~~~~~~~~~~~~

List the relevant filter values of the ``get`` command using the :func:`altimetry_downloader_aviso.filter_infos()` function.

.. code-block:: pycon

    >>> product = get_product_from_short_name("SWOT_L3_LR_SSH_Basic")
    >>> temporal_coverage, half_orbit_range, versions = filter_infos(product)
    >>> print(temporal_coverage)
    {'CALVAL': [2023-03-28T23:44:17.000000, 2023-07-10T09:12:05.000000], 'SCIENCE': [2023-07-26T12:27:56.000000, 2026-06-22T20:46:05.000000]}
    >>> print(half_orbit_range)
    {'CALVAL': ((474, 3), (578, 4)), 'SCIENCE': ((1, 149), (52, 99))}
    >>> print(versions)
    {'1.0.2', '3.0', '2.0', '2.0.1'}

Subsetting a product
~~~~~~~~~~~~~~~~~~~~

Subset a product using :func:`altimetry_downloader_aviso.subset()` function.

.. code-block:: pycon

    >>> local_files = subset("SWOT_L3_LR_SSH_Basic", box=(-10, 10, 10, 40), selected_variables=["ssha_unfiltered", "time"], output_dir="aviso_dir", cycle_number=1, pass_number=[223, 225, 236], version="3.0")
    >>> print(local_files)
    ['aviso_dir/SWOT_L3_LR_SSH_Basic_001_223_20230729T035501_20230729T044628_v3.0.nc',
     'aviso_dir/SWOT_L3_LR_SSH_Basic_001_236_20230729T150350_20230729T155516_v3.0.nc']


Further Reading
---------------

- :doc:`../basic_usage/advanced_usage`
