import os
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QMessageBox
from lynowcut.app import MainWindow


class PdfConsentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pdf_flattening_requires_explicit_confirmation(self):
        window = MainWindow()
        try:
            self.assertFalse(window.build_options().flatten_pdf)
            with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.No):
                window.flatten_pdf.click()
            self.assertFalse(window.build_options().flatten_pdf)
            with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes):
                window.flatten_pdf.click()
            self.assertTrue(window.build_options().flatten_pdf)
            window.flatten_pdf.click()
            self.assertFalse(window.build_options().flatten_pdf)
        finally:
            window.close()
