Authentication
==============

The download and subsetting requests to the AVISO Thredds Data Server require user authentication.
To get credentials, please register at `AVISO User Registration <https://www.aviso.altimetry.fr/en/data/data-access/registration-form.html>`_.

This module handles authentication through two files:

- ``.netrc``: standard UNIX-style mechanism to store login credentials associated with
  specific hosts. Once saved, the user's credentials can be reused for all requests.
- ``.ncrc``: configuration file for the netCDF4 backend. It is set up so that the
  credentials stored in the ``.netrc`` file will be used.

Both files are located in ``~/.altimetry`` to isolate the downloader from already
existing user configurations.

Overview
--------

When the module sets up authentication, it proceeds as follows:

1. Checks if a valid ``.ncrc`` file exists. If it does not exist, misses the
   ``HTTP.NETRC`` entry or has an obsolete value, it will be created/updated accordingly.
2. Checks if a valid ``.netrc`` file exists in the user's home directory. If it does not
   exist or does not contain the expected host entry, the user is prompted to enter
   their credentials interactively. Once the credentials are provided, ``.netrc`` file
   is created or updated accordingly.
3. Setup the ``NETRC`` and ``NCRCENV_RC`` environment variables for the ``requests`` and
   ``netCDF4`` modules.
4. Future requests reuse the stored credentials automatically.

File Format
------------

The ``.netrc`` file should contain:

.. code-block:: none

   machine tds-odatis.aviso.altimetry.fr
    login <user_login>
    password <user_password>

Note that ``user_login`` is typically an email address associated with the user's account.

The ``.ncrc`` file should contain an entry similar to:

.. code-block:: none

   HTTP.NETRC=/path/to/user/home/.altimetry/.netrc


Example Usage
-------------

.. code-block:: python

   from altimetry_downloader_aviso import get
   get("SWOT_L3_LR_SSH_Basic", output_dir="aviso_dir", cycle_number=7, pass_number=[12, 13])

If no ``.netrc`` file is found, the module will prompt for credentials:

.. code-block:: console

   Username: my_username
   Password: ...

The credentials are then written to the ``.netrc`` file for future use.

Error Handling
--------------

If the ``.netrc`` file is malformed or credentials are invalid, the module will display
a warning message.

If the authentication is set up after the importing the ``netCDF4`` module, the settings
will not be properly applied and a warning message is emitted. Users are encouraged to
first setup the authentication and then import their code if said-code import netCDF4.

.. tab-set::

   .. tab-item:: Effective authentication

      .. code-block:: python

         import altimetry_downloader_aviso as ada
         ada.ensure_credentials(ada.tds_client.TDS_HOST)
         import <user specific code importing netCDF4>

   .. tab-item:: Broken authentication

      .. code-block:: python

         >>> import altimetry_downloader_aviso as ada
         >>> import <user specific code importing netCDF4>
         altimetry_downloader_aviso/auth.py:80: UserWarning: netCDF4 is already loaded. Authentication configuration may not be applied


See Also
--------

- `Python netrc module documentation <https://docs.python.org/3/library/netrc.html>`_
- `netcdf-c environment variables reference <https://docs.unidata.ucar.edu/netcdf-c/4.10.0/nc_env_quickstart.html#nc_env_vars>`_
