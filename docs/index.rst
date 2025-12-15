Altimetry Downloader Aviso documentation
========================================

This documentation covers the main public API of the ``altimetry-downloader-aviso`` package.
The Altimetry Downloader Aviso is a tool to easily search and download altimetry products from the Aviso catalog.
It provides both a Command Line Interface (CLI) and a Python Interface (API),
offering these capabilities:

   - Metadata information: list products available and retrieve their metadata information
   - Download data: apply filters to download files in their original NetCDF format, via `AVISO's Thredds Data Server <https://tds-odatis.aviso.altimetry.fr>`_ using HTTPS connection.


.. warning::

   This is an early release of the Altimetry Downloader Aviso client.
   The API is only configured to retrieve Swot/CDS-AVISO products.

.. toctree::
   :maxdepth: 1
   :caption: GETTING STARTED

   getting_started/installation
   getting_started/command_line_interface
   getting_started/python_interface

.. toctree::
   :maxdepth: 1
   :caption: USER GUIDE

   basic_usage/authentication
   basic_usage/advanced_usage

.. toctree::
   :maxdepth: 1
   :caption: REFERENCE

   api
   changelog


Indices et tables
=================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
