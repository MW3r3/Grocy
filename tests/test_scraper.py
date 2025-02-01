import os
import pytest
import warnings
from unittest.mock import patch, MagicMock
from app.scraper import download_pdfs_from_lidl, download_pdfs_from_maxima

@pytest.fixture
def mock_driver(mocker):
    mock_driver = MagicMock()
    mocker.patch('selenium.webdriver.Chrome', return_value=mock_driver)
    return mock_driver

def test_download_pdfs_from_lidl(mock_driver):
    download_dir = os.path.join(os.getcwd(), "test_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Mock the find_elements method to return a list of mock elements
    mock_element = MagicMock()
    mock_element.get_attribute.return_value = "http://example.com/test.pdf"
    mock_driver.find_elements.return_value = [mock_element]
    
    download_pdfs_from_lidl(download_dir)
    
    # Assert that the driver.get method was called with the PDF URL
    mock_driver.get.assert_any_call("http://example.com/test.pdf")
    
    # Clean up
    os.rmdir(download_dir)

def test_download_pdfs_from_maxima(mock_driver):
    download_dir = os.path.join(os.getcwd(), "test_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Mock the find_elements method to return a list of mock elements
    mock_element = MagicMock()
    mock_element.get_attribute.return_value = "http://example.com/test.pdf"
    mock_driver.find_elements.return_value = [mock_element]
    
    download_pdfs_from_maxima(download_dir)
    
    # Assert that the driver.get method was called with the PDF URL
    mock_driver.get.assert_any_call("http://example.com/test.pdf")
    
    # Clean up
    os.rmdir(download_dir)

def test_no_pdfs_found_lidl(mock_driver):
    download_dir = os.path.join(os.getcwd(), "test_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Mock the find_elements method to return an empty list
    mock_driver.find_elements.return_value = []
    
    with patch('app.scraper.logger') as mock_logger:
        download_pdfs_from_lidl(download_dir)
        mock_logger.warning.assert_called_with("No PDF links found on https://www.lidl.lv/")
        warnings.warn("No PDF links found on https://www.lidl.lv/")
    
    # Clean up
    os.rmdir(download_dir)

def test_no_pdfs_found_maxima(mock_driver):
    download_dir = os.path.join(os.getcwd(), "test_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Mock the find_elements method to return an empty list
    mock_driver.find_elements.return_value = []
    
    with patch('app.scraper.logger') as mock_logger:
        download_pdfs_from_maxima(download_dir)
        mock_logger.warning.assert_called_with("No PDF links found on https://www.maxima.lv/")
        warnings.warn("No PDF links found on https://www.maxima.lv/")
    
    # Clean up
    os.rmdir(download_dir)