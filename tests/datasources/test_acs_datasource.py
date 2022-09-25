import pathlib
import zipfile

import numpy as np
import pytest

from folktables.datasources.acs_datasource import ACSDataSource
from folktables.datasources.acs_datasource import generate_categories

# We've made artificial datasets that contain the same columns and file
# location as the real surveys, but only contain 5 rows (which will reduce the
# overhead of our testing.
# The surveys that we've artificially created correspond to:
# - Survey year = 2016, horizon = 5-Year, survey = person, states = [TN]
# - Survey year = 2017, horizon = 1-Year, survey = person, states = [TN]
# - Survey year = 2018, horizon = 5-Year, survey = household, states = [TN]

# Location where the artificial data is stored.
ACS_LOCAL_DATA_FILE_PATH = 'tests/datasources/data'
FILE_2016 = f'{ACS_LOCAL_DATA_FILE_PATH}/2016/5-Year/ss16ptn.csv'
FILE_2017 = f'{ACS_LOCAL_DATA_FILE_PATH}/2017/1-Year/psam_p47.csv'
FILE_2018 = f'{ACS_LOCAL_DATA_FILE_PATH}/2018/5-Year/psam_h47.csv'

# Names of the zip files to be created (these are the same name as those
# generated by the the Census's website).
ZIP_NAME_2016 = 'csv_ptn.zip'
ZIP_NAME_2017 = 'csv_ptn.zip'
ZIP_NAME_2018 = 'csv_htn.zip'

# The URLs where the data is found.
BASE_URL = 'https://www2.census.gov/programs-surveys/acs/data/pums/'
URL_2016_DATA = f'{BASE_URL}2016/5-Year/{ZIP_NAME_2016}'
URL_2017_DATA = f'{BASE_URL}2017/1-Year/{ZIP_NAME_2017}'
URL_2018_DATA = f'{BASE_URL}2018/5-Year/{ZIP_NAME_2018}'


def generate_zip_file(file_to_zip, zip_name):
    """Zips some files and returns it as a bytes object.
    This method will help us mock the HTTP requests.

    Parameters
    ----------
    file_to_zip : pathlib.Path
        Pahtlib to where the data we want to zip is being stored.
    zip_name : str
        Name to be given to the zip file (i.e., file path and file name of
        where the Zip file will be stored).

    Returns
    -------
    bytes
        The bytes of the zip file that was just created.
    """
    # Zip the artificially created dataset.
    with zipfile.ZipFile(zip_name, mode='w') as archive:
        archive.write(file_to_zip, arcname=file_to_zip.name)

    # Read and return the zip file as a bytes object.
    with open(zip_name, mode='rb') as zipped_data:
        return zipped_data.read()


def test_acs_data_source_constructor():
    """Tests the constructor for the ACSDAtaSource object."""
    # Tests we catch instances in which the user passes an invalid year.
    with pytest.raises(ValueError):
        ACSDataSource(survey_year='2000',
                      horizon='1-Year',
                      survey='person',
                      root_dir='data')

    # Test we catch instances in which the horizon the user passes is an
    # invalid value.
    with pytest.raises(ValueError):
        ACSDataSource(survey_year='2015',
                      horizon='2-Year',
                      survey='person',
                      root_dir='data')

    # Test we catch instances in which the user passes an invalid survey type.
    with pytest.raises(ValueError):
        ACSDataSource(survey_year='2015',
                      horizon='1-Year',
                      survey='invalid value',
                      root_dir='data')

    # Tests we can successfully create an ACSDataSource object.
    acs_ds = ACSDataSource(survey_year='2015',
                           horizon='1-Year',
                           survey='person',
                           root_dir='data')

    assert isinstance(acs_ds, ACSDataSource)


def test_get_data_without_download():
    """Tests we can successfully retrieve a dataset stored in local memory."""
    acs_ds = ACSDataSource(survey_year='2016',
                           horizon='5-Year',
                           survey='person',
                           root_dir=ACS_LOCAL_DATA_FILE_PATH)
    data = acs_ds.get_data(states=['TN'])
    assert data.shape == (5, 283)

    acs_ds = ACSDataSource(survey_year='2017',
                           horizon='1-Year',
                           survey='person',
                           root_dir=ACS_LOCAL_DATA_FILE_PATH)
    data = acs_ds.get_data(states=['TN'])
    assert data.shape == (5, 286)

    acs_ds = ACSDataSource(survey_year='2018', horizon='5-Year',
                           survey='household',
                           root_dir=ACS_LOCAL_DATA_FILE_PATH)
    data = acs_ds.get_data(states=['TN'])
    assert data.shape == (5, 237)


def test_get_data_with_download(tmp_path, requests_mock):
    """Tests we can successfully retrieve a dataset when we have to download
    it from an endpoint.
    """
    # One nice work around to this is that we can capture that HTTP request
    # and we can just create a ZIP file with the already downloaded dataset
    # and return that instead of having to make an HTTP request to the
    # actual web server.
    zip_name = tmp_path / ZIP_NAME_2016
    zip_bytes = generate_zip_file(pathlib.Path(FILE_2016), str(zip_name))

    requests_mock.get(URL_2016_DATA, content=zip_bytes)
    acs_ds = ACSDataSource(survey_year='2016',
                           horizon='5-Year',
                           survey='person',
                           root_dir=str(tmp_path))
    data = acs_ds.get_data(states=['TN'], download=True)
    assert data.shape == (5, 283)
    assert pathlib.Path(f'{tmp_path}/2016/5-Year/ss16ptn.csv').is_file()


    zip_name = tmp_path / ZIP_NAME_2017
    zip_bytes = generate_zip_file(pathlib.Path(FILE_2017), str(zip_name))

    requests_mock.get(URL_2017_DATA, content=zip_bytes)
    acs_ds = ACSDataSource(survey_year='2017',
                           horizon='1-Year',
                           survey='person',
                           root_dir=str(tmp_path))
    data = acs_ds.get_data(states=['TN'], download=True)
    assert data.shape == (5, 286)
    assert pathlib.Path(f'{tmp_path}/2017/1-Year/psam_p47.csv').is_file()

    zip_name = tmp_path / ZIP_NAME_2018
    zip_bytes = generate_zip_file(pathlib.Path(FILE_2018), str(zip_name))

    requests_mock.get(URL_2018_DATA, content=zip_bytes)
    acs_ds = ACSDataSource(survey_year='2018',
                           horizon='5-Year',
                           survey='household',
                           root_dir=str(tmp_path))
    data = acs_ds.get_data(states=['TN'], download=True)
    assert data.shape == (5, 237)
    assert pathlib.Path(f'{tmp_path}/2018/5-Year/psam_h47.csv').is_file()


def test_get_data_with_download_false(tmp_path):
    """Tests that an error is raised if hte user wants to retrieve files that
    don't exist in the user's local machine and doesn't set `download=True` in
    the `get_data` method.
    """
    acs_ds = ACSDataSource(survey_year='2018',
                           horizon='5-Year',
                           survey='household',
                           root_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        acs_ds.get_data(states=['TN'])


def test_get_data_when_states_are_passed():
    """Tests that we can retrieve the data when the user passes a list of
    states.
    """
    # Test that we're robust to the instance in which the user doesn't
    # appropriately capitalize the state abbreviations.
    acs_ds = ACSDataSource(survey_year='2016',
                           horizon='5-Year',
                           survey='person',
                           root_dir=ACS_LOCAL_DATA_FILE_PATH)
    data = acs_ds.get_data(states=['tn'])
    assert data.shape == (5, 283)

    # Test that we can catch the instance in which the user passes an
    # invalid state. This should raise a `ValueError`.
    acs_ds = ACSDataSource(survey_year='2016',
                           horizon='5-Year',
                           survey='person',
                           root_dir=ACS_LOCAL_DATA_FILE_PATH)
    with pytest.raises(ValueError):
        data = acs_ds.get_data(states=['invalid_state'])


def test_get_data_with_join_household():
    """Tests that we can retrieve the data and join based on household."""
    # Test we can successfully retrieve the data.
    acs_ds = ACSDataSource(survey_year='2018', horizon='5-Year',
                           survey='household',
                           root_dir=ACS_LOCAL_DATA_FILE_PATH)
    data = acs_ds.get_data(states=['TN'], join_household=True)
    assert data.shape == (5, 237)

    # Test we can catch the instance in which the user wants to join based on
    # the household, but the survey type is not `person`.
    acs_ds = ACSDataSource(survey_year='2016',
                           horizon='5-Year',
                           survey='person',
                           root_dir=ACS_LOCAL_DATA_FILE_PATH)
    with pytest.raises(ValueError):
        acs_ds.get_data(states=['TN'], join_household=True)


def test_definitions_download(tmp_path):
    """Tests we can download the definitions."""
    # Note: I'm leaving the test, for the most part, as it was originally
    # written. One improvement would be to capture the request and return
    # a known df that we can just test.
    data_source = ACSDataSource(survey_year='2018',
                                horizon='1-Year',
                                survey='person',
                                root_dir=str(tmp_path))
    definition_df = data_source.get_definitions(download=True)

    # test some definition_df properties
    assert len(definition_df.columns) == 7
    assert (np.isin(definition_df[0].unique(), ['NAME', 'VAL'])).all()
    assert (np.isin(definition_df[2].unique(), ['C', 'N'])).all()
