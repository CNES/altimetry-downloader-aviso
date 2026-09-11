Release Notes
=============

0.7.0 (2026-09-11)
------------------

Added
~~~~~

Added an optional download progress bar for the ``get`` command and function,
showing bytes transferred and speed as files are downloaded. The CLI shows
the progress bar by default; use ``--no-progress`` to disable it. The Python
API (``get()``) hides it by default; pass ``show_progress=True`` to enable it.

Changed
~~~~~~~

File-level "downloaded" log messages are now emitted at ``DEBUG`` level
instead of ``INFO`` when the progress bar is active, to avoid interleaving
with its display.


0.6.0 (2026-09-08)
------------------

A new dependency to ``altimetry-search`` has been added to the project. This library is used
to query the cycles of Swot mission, if a time filter is provided to the ``get`` or ``subset`` commands.
It is also used to query the half-orbits that are crossing a given bounding box, if a box filter is provided to the ``get`` or ``subset`` commands.

Added a new ``box`` filter to the ``get`` command. This new filter allows to download passes that are crossing a given bounding box.

Added a total download size estimate and a confirmation prompt before
downloading granules. The CLI (``altimetry-downloader-aviso get``) shows
the prompt by default; use ``--yes``/``-y`` to skip it. The Python API
(``get()``) skips the prompt by default (``assume_yes=True``) to avoid
blocking non-interactive callers; pass ``assume_yes=False`` to enable it.


0.5.0 (2026-07-07)
------------------

Added a new ``subset`` subcommand to subset granules over the OpenDAP protocol. This
new command should help reduce the bandwidth usage by selecting an area of interest and
a set of variables to download.

.. important::

    Subsetting support is partial and has not been implemented for all products. Please
    refer to the subcommand documentation for the exhaustive list of supported products.

Authentication has been reworked to be compatible with the new ``subset`` subcommand. It
relies on the configuration mechanisms of the netCDF4 and requests libraries. In
addition, the credential files are now isolated to avoid conflicts with existing user
configurations. Expect the new version to prompt again for the AVISO credentials.

Compatibility issues with Windows have been addressed. `#1 <https://github.com/CNES/altimetry-downloader-aviso/issues/1>`_.

0.4.0 (2026-06-25)
------------------

Added a new ``help-query`` subcommand to give additional information about the temporal coverage,
half orbit range and versions of a given product. This should be useful to configure the parameters
of the ``get`` command.

``files_collections`` dependency has been bumped to v2.0.0. This version introduces the necessary
features for the ``help-query`` subcommand.

A list of supported products is now enforced. This will prevent listing new products added on the server
without any prior validation on the client side. See the related issue `#4 <https://github.com/CNES/altimetry-downloader-aviso/issues/4>`_.


0.3.2 (2026-04-28)
------------------

The 3.0 version of the "Multimission Gridded (with SWOT, MIOST only) Level-4 Sea Surface Heights and Velocities" product has been added to the list of supported products.


0.3.1 (2026-03-06)
------------------

Update project urls.

0.3.0 (2026-02-04)
------------------

Handle breaking changes from bumping ``files-collections`` dependency to v1.0.0.

0.2.2 (2026-01-07)
------------------

Get command returns the list of local file paths even when no files are downloaded because
they already exist locally.

0.2.1 (2025-12-15)
------------------

The L3 LR SSH Technical product has been added to the list of supported products.


0.1.0 (2025-12-10)
------------------

This version is the first beta version of the downloader. It introduces the three main
features of the CLI and Python interfaces:

* summary
* details
* get

Only SWOT mission datasets can be retrieved in this version. Additionally, the available
filters for selecting granules are limited to product version, temporal extent, and
half-orbit number.
