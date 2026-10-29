import hashlib
import io
import subprocess
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pikepdf
from PIL import Image
from lynowcut.engine import Cancelled, Options, process
from lynowcut import media_install


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_pdf_default_preserves_text_link_and_form_even_when_target_is_unreachable(self):
        src = self.root / 'interactive.pdf'
        with pikepdf.new() as pdf:
            page = pdf.add_blank_page()
            font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
            page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
            page.Contents = pdf.make_stream(b'BT /F1 12 Tf 20 20 Td (Searchable text) Tj ET\n' * 300)
            link = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Link, Rect=[0, 0, 100, 100], A=pikepdf.Dictionary(S=pikepdf.Name.URI, URI='https://example.org')))
            field = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Widget, FT=pikepdf.Name.Tx, T='name', V='kept', Rect=[100, 100, 200, 120]))
            page.Annots = [link, field]
            pdf.Root.AcroForm = pikepdf.Dictionary(Fields=[field])
            pdf.save(src, compress_streams=False)
        digest = hashlib.sha256(src.read_bytes()).digest()
        with patch('pypdfium2.PdfDocument', side_effect=AssertionError('Rasterization must be opt-in')):
            result = process(src, self.root / 'out', Options(max_mb=.00001))
        self.assertEqual(result.status, 'Meta não atingida')
        with pikepdf.open(result.output) as pdf:
            self.assertIn(b'Searchable text', pdf.pages[0].Contents.read_bytes())
            self.assertEqual(str(pdf.pages[0].Annots[0].A.URI), 'https://example.org')
            self.assertEqual(str(pdf.Root.AcroForm.Fields[0].V), 'kept')
        self.assertEqual(hashlib.sha256(src.read_bytes()).digest(), digest)

    def test_signed_office_and_odf_are_rejected(self):
        for marker in ('_xmlsignatures/sig1.xml', 'META-INF/documentsignatures.xml', 'META-INF/macrosignatures.xml', 'META-INF/signatures.xml'):
            with self.subTest(marker=marker):
                src = self.root / 'signed.docx'
                with zipfile.ZipFile(src, 'w') as archive:
                    archive.writestr(marker, '<Signature/>')
                with self.assertRaisesRegex(ValueError, 'assinatura'):
                    process(src, self.root / 'out', Options())
                self.assertFalse(list((self.root / 'out').glob('*lynowcut*')))

    def test_pdf_cancellation_is_not_swallowed_by_visual_fallback(self):
        src = self.root / 'photo.pdf'
        Image.effect_noise((800, 600), 80).convert('RGB').save(src, 'PDF', quality=98)
        event = threading.Event()
        def progress(message):
            event.set()
        with self.assertRaises(Cancelled):
            process(src, self.root / 'out', Options(reduction=90, flatten_pdf=True), event, progress)
        self.assertFalse(list((self.root / 'out').iterdir()))

    def media_archive(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('ffmpeg/bin/ffmpeg.exe', b'fake ffmpeg')
            archive.writestr('ffmpeg/bin/ffprobe.exe', b'fake ffprobe')
        return buffer.getvalue()

    def test_media_install_is_atomic_and_validates_version_and_codecs(self):
        data = self.media_archive()
        def runner(args, **kwargs):
            text = b'libx264 aac libmp3lame' if '-encoders' in args else f'ffmpeg version {media_install.VERSION}\n'.encode()
            return subprocess.CompletedProcess(args, 0, text, b'')
        with patch.object(media_install, 'SHA256', hashlib.sha256(data).hexdigest()):
            target = media_install.install(self.root, opener=lambda *a, **kw: io.BytesIO(data), runner=runner)
        self.assertEqual({p.name for p in target.iterdir()}, {'ffmpeg.exe', 'ffprobe.exe'})
        self.assertFalse(list(self.root.glob('.media-*')))

    def test_media_bad_hash_and_cancel_leave_no_install(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(Cancelled):
            media_install.install(self.root, event, opener=lambda *a, **kw: io.BytesIO(b'bad'))
        with self.assertRaisesRegex(RuntimeError, 'SHA-256'):
            media_install.install(self.root, opener=lambda *a, **kw: io.BytesIO(b'bad'))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_media_failed_validation_and_unwritable_destination_leave_no_install(self):
        data = self.media_archive()
        with patch.object(media_install, 'SHA256', hashlib.sha256(data).hexdigest()):
            with self.assertRaises(subprocess.CalledProcessError):
                media_install.install(self.root, opener=lambda *a, **kw: io.BytesIO(data), runner=lambda *a, **kw: (_ for _ in ()).throw(subprocess.CalledProcessError(1, a)))
        with patch('pathlib.Path.mkdir', side_effect=PermissionError('read only')):
            with self.assertRaises(PermissionError):
                media_install.install(self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_media_download_limit(self):
        with patch.object(media_install, 'MAX_DOWNLOAD', 2):
            with self.assertRaisesRegex(RuntimeError, 'limite'):
                media_install.install(self.root, opener=lambda *a, **kw: io.BytesIO(b'large'))
        self.assertEqual(list(self.root.iterdir()), [])
