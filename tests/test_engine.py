import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from PIL import Image
import pikepdf
from lynowcut.engine import Cancelled, Options, process

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root/'out'
        self.image = self.root/'photo.bmp'
        Image.effect_noise((320, 240), 70).convert('RGB').save(self.image)

    def tearDown(self):
        self.temp.cleanup()

    def test_image_target_dimensions_original_and_collision(self):
        digest = hashlib.sha256(self.image.read_bytes()).hexdigest()
        a = process(self.image, self.out, Options(reduction=30))
        b = process(self.image, self.out, Options(reduction=30))
        self.assertEqual(a.status, 'Meta atingida')
        self.assertLessEqual(a.after, a.target)
        self.assertNotEqual(a.output, b.output)
        with Image.open(a.output) as img:
            self.assertEqual(img.size, (320, 240))
        self.assertEqual(hashlib.sha256(self.image.read_bytes()).hexdigest(), digest)

    def test_unreachable_target_reported(self):
        r = process(self.image, self.out, Options(max_mb=.00001))
        self.assertEqual(r.status, 'Meta não atingida')
        self.assertGreater(r.after, r.target)
        self.assertTrue(Path(r.output).is_file())

    def test_aggressive_target_can_resize_proportionally(self):
        src = self.root/'large-noise.jpg'
        Image.effect_noise((1200, 900), 90).convert('RGB').save(src, quality=96)
        r = process(src, self.out, Options(reduction=90, min_quality=40, resize_to_target=True))
        self.assertEqual(r.status, 'Meta atingida')
        with Image.open(r.output) as result:
            self.assertLess(result.width, 1200)
            self.assertAlmostEqual(result.width/result.height, 1200/900, places=2)

    def test_transparency_kept_and_jpeg_rejected(self):
        src = self.root/'alpha.png'
        Image.new('RGBA', (60, 60), (200, 80, 20, 0)).save(src)
        r = process(src, self.out, Options())
        if r.output:
            with Image.open(r.output) as img:
                self.assertEqual(img.convert('RGBA').getpixel((1, 1))[3], 0)
        with self.assertRaisesRegex(ValueError, 'transparência'):
            process(src, self.out, Options(image_format='JPEG'))

    def test_animated_input_rejected(self):
        src = self.root/'animated.webp'
        Image.new('RGB', (30,30), 'red').save(src, save_all=True, append_images=[Image.new('RGB', (30,30), 'blue')], duration=200, loop=0)
        with self.assertRaisesRegex(ValueError, 'animada'):
            process(src, self.out, Options())

    def test_metadata_removal(self):
        src = self.root/'metadata.tiff'
        exif = Image.Exif()
        exif[315] = 'Private author'
        Image.effect_noise((320,240), 50).convert('RGB').save(src, exif=exif)
        r = process(src, self.out, Options(image_format='JPEG'))
        self.assertIsNotNone(r.output)
        with Image.open(r.output) as img:
            self.assertNotIn(315, img.getexif())

    def test_cancel_preserves_original_no_output(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(Cancelled):
            process(self.image, self.out, Options(), event)
        self.assertTrue(self.image.exists())
        self.assertFalse(self.out.exists())

    def test_zip_roundtrip(self):
        src = self.root/'raw.txt'
        src.write_text('LynowCut\n'*10000)
        r = process(src, self.out, Options(action='Criar ZIP'))
        with zipfile.ZipFile(r.output) as archive:
            self.assertEqual(archive.read(src.name), src.read_bytes())

    def test_docx_container_and_embedded_image_are_optimized(self):
        src = self.root/'presentation.docx'
        image_data = io.BytesIO()
        Image.effect_noise((500, 400), 80).convert('RGB').save(image_data, 'JPEG', quality=98)
        image_data.seek(0)
        with zipfile.ZipFile(src, 'w', zipfile.ZIP_STORED) as document:
            document.writestr('[Content_Types].xml', '<Types/>')
            document.writestr('word/document.xml', '<document/>')
            document.writestr('word/media/photo.jpg', image_data.read())
        result = process(src, self.out, Options(min_quality=50))
        self.assertEqual(Path(result.output).suffix, '.docx')
        self.assertLess(result.after, result.before)
        with zipfile.ZipFile(result.output) as document:
            self.assertEqual(document.read('word/document.xml'), b'<document/>')
            self.assertTrue(document.testzip() is None)

    def test_pdf_preserves_pages_text_and_original(self):
        src = self.root/'document.pdf'
        with pikepdf.new() as pdf:
            page = pdf.add_blank_page()
            page.Contents = pdf.make_stream(b'BT /F1 12 Tf 10 10 Td (LynowCut test) Tj ET\n'*100)
            pdf.docinfo['/Author'] = 'Private author'
            pdf.save(src, compress_streams=False, object_stream_mode=pikepdf.ObjectStreamMode.disable)
        digest = src.read_bytes()
        r = process(src, self.out, Options())
        self.assertIsNotNone(r.output)
        with pikepdf.open(r.output) as pdf:
            self.assertEqual(len(pdf.pages), 1)
            self.assertIn(b'LynowCut test', pdf.pages[0].Contents.read_bytes())
            self.assertNotIn('/Author', pdf.docinfo)
        self.assertEqual(src.read_bytes(), digest)

    def test_photo_pdf_uses_visual_fallback_for_aggressive_goal(self):
        src = self.root/'photo.pdf'
        Image.effect_noise((1200, 900), 80).convert('RGB').save(src, 'PDF', quality=98)
        result = process(src, self.out, Options(reduction=80, min_quality=35, flatten_pdf=True))
        self.assertEqual(result.status, 'Meta atingida')
        self.assertLessEqual(result.after, result.target)
        self.assertIn('compactado visualmente', result.note)

    def test_signed_pdf_rejected(self):
        src = self.root/'signed.pdf'
        with pikepdf.new() as pdf:
            pdf.add_blank_page()
            pdf.Root.AcroForm = pikepdf.Dictionary(SigFlags=3)
            pdf.save(src)
        with self.assertRaisesRegex(ValueError, 'assinatura'):
            process(src, self.out, Options())

    def test_invalid_target(self):
        for mb in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                Options(max_mb=mb).target(100)

    @unittest.skipUnless(os.environ.get('LYNOWCUT_REQUIRE_MEDIA') or (shutil.which('ffmpeg') and shutil.which('ffprobe')), 'FFmpeg não disponível (não permitido no CI de publicação)')
    def test_video_two_pass_and_extract(self):
        src = self.root/'video.avi'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=160x120:rate=15', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '2', '-c:v', 'mpeg4', '-q:v', '2', '-c:a', 'pcm_s16le', str(src)], check=True)
        r = process(src, self.out, Options(max_mb=.12))
        self.assertIsNotNone(r.output)
        self.assertEqual(Path(r.output).suffix, '.mp4')
        self.assertLess(r.after, r.before)
        self.assertLessEqual(r.after, r.target)
        audio = process(src, self.out, Options(action='Extrair áudio', max_mb=.05))
        self.assertEqual(Path(audio.output).suffix, '.mp3')
        self.assertTrue(Path(audio.output).stat().st_size > 0)

if __name__ == '__main__':
    unittest.main()
