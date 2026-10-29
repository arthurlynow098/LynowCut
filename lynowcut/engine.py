"""Local processing. Originals are never replaced; each result is measured."""
from __future__ import annotations
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

IMAGES = {'.jpg', '.jpeg', '.jfif', '.png', '.webp', '.bmp', '.tif', '.tiff', '.gif', '.avif', '.heic', '.heif'}
VIDEOS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.wmv', '.flv', '.mpeg', '.mpg', '.mts', '.m2ts', '.ts', '.3gp'}
AUDIO = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus', '.aif', '.aiff'}
DOCUMENTS = {'.docx', '.docm', '.pptx', '.pptm', '.xlsx', '.xlsm', '.odt', '.ods', '.odp', '.epub'}
SUPPORTED = IMAGES | VIDEOS | AUDIO | DOCUMENTS | {'.pdf'}

class Cancelled(Exception):
    pass

@dataclass(frozen=True)
class Options:
    reduction: float = 30
    max_mb: float | None = None
    image_format: str = 'WebP'
    min_quality: int = 40
    remove_metadata: bool = True
    action: str = 'Comprimir'
    start: float = 0
    duration: float | None = None
    resize_to_target: bool = True
    flatten_pdf: bool = False

    def target(self, size: int) -> int:
        if not 1 <= self.reduction <= 95:
            raise ValueError('A redução deve estar entre 1 e 95%.')
        if self.max_mb is not None and (not math.isfinite(self.max_mb) or self.max_mb <= 0):
            raise ValueError('Informe um tamanho positivo em MB.')
        if not 1 <= self.min_quality <= 95:
            raise ValueError('Qualidade mínima inválida.')
        if not math.isfinite(self.start) or self.start < 0:
            raise ValueError('O início deve ser positivo ou zero.')
        if self.duration is not None and (not math.isfinite(self.duration) or self.duration <= 0):
            raise ValueError('A duração deve ser positiva.')
        return max(1, int(self.max_mb * 1_000_000 if self.max_mb else size * (1-self.reduction/100)))

@dataclass
class Result:
    source: str
    output: str | None
    before: int
    after: int
    target: int
    status: str
    note: str = ''

    @property
    def saved(self):
        return self.before - self.after if self.output else 0


def resource(relative: str) -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1])) / relative


def binary(name: str) -> str:
    from .media_install import VERSION
    suffix = '.exe' if os.name == 'nt' else ''
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    candidates = [root / f'media-{VERSION}' / (name+suffix), resource(f'bin/{name}{suffix}'), root / 'bin' / (name+suffix)]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError(f'{name} não encontrado. Coloque {name}{suffix} na pasta bin ao lado do programa ou instale no PATH.')


def check_cancel(event):
    if event.is_set():
        raise Cancelled('Cancelado. Os originais foram preservados.')


def run(args, event, *, timeout=3600):
    check_cancel(event)
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    # File-backed streams prevent a full stderr/stdout pipe from blocking cancellation.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(args, stdout=out, stderr=err, stdin=subprocess.DEVNULL, creationflags=flags)
        begun = time.monotonic()
        try:
            while process.poll() is None:
                check_cancel(event)
                if time.monotonic()-begun > timeout:
                    raise RuntimeError('Tempo limite de processamento excedido.')
                event.wait(.12)
            if process.returncode:
                err.seek(0, 2)
                length = err.tell()
                err.seek(max(0, length-2000))
                raise RuntimeError(err.read().decode('utf-8', errors='replace').strip() or 'Falha ao processar o arquivo.')
            out.seek(0)
            return out.read()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def image_compress(src, dst, options, target, event, progress):
    fmt = options.image_format.upper()
    if fmt not in {'WEBP', 'JPEG', 'PNG', 'AVIF'}:
        raise ValueError('Formato de imagem inválido.')
    with Image.open(src) as opened:
        if getattr(opened, 'n_frames', 1) > 1:
            raise ValueError('Imagem animada ou multipágina: não será achatada. Use um arquivo de quadro único.')
        icc = opened.info.get('icc_profile')
        img = ImageOps.exif_transpose(opened).copy()
    # Preserve a color profile even when privacy metadata is removed.
    metadata = {'icc_profile': icc} if icc else {}
    if not options.remove_metadata:
        exif = img.getexif().tobytes()
        if exif:
            metadata['exif'] = exif
    img.info.clear()
    if fmt == 'JPEG':
        if 'A' in img.getbands() or 'transparency' in opened.info:
            raise ValueError('JPEG não mantém transparência. Escolha WebP ou PNG.')
        img = img.convert('RGB')
    elif img.mode not in {'RGB', 'RGBA', 'L', 'LA'}:
        img = img.convert('RGBA')
    original_size = img.size

    def encode(image, q):
        stream = io.BytesIO()
        if fmt == 'PNG':
            image.save(stream, format=fmt, optimize=True, **metadata)
        elif fmt == 'AVIF':
            image.save(stream, format=fmt, quality=q, speed=6, **metadata)
        else:
            image.save(stream, format=fmt, quality=q, **({'method': 6} if fmt == 'WEBP' else {'optimize': True, 'progressive': True}), **metadata)
        return stream.getvalue()
    if fmt == 'PNG':
        check_cancel(event)
        data = encode(img, 95)
        resized = False
        while len(data) > target and options.resize_to_target and min(img.size) > 240:
            ratio = max(.65, min(.92, math.sqrt(target / len(data)) * .96))
            new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
            if new_size == img.size:
                break
            progress(f'Otimizando resolução · {new_size[0]}×{new_size[1]}')
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            data = encode(img, 95)
            resized = True
        dst.write_bytes(data)
        if resized:
            return f'PNG: resolução ajustada de {original_size[0]}×{original_size[1]} para {img.width}×{img.height}; pixels foram alterados.'
        return 'PNG otimizado sem alterar pixels; a meta pode não ser alcançada.'

    def quality_search(image):
        low, high = options.min_quality, 95
        smallest = best = None
        while low <= high:
            check_cancel(event)
            q = (low + high) // 2
            progress(f'Ajustando qualidade · {q}%')
            data = encode(image, q)
            if smallest is None or len(data) < len(smallest):
                smallest = data
            if len(data) <= target:
                best = data
                low = q + 1
            else:
                high = q - 1
        return best, smallest

    best, smallest = quality_search(img)
    resized = False
    # For aggressive targets, quality alone is insufficient. Reduce pixels in
    # controlled steps while preserving aspect ratio until the byte budget fits.
    while best is None and options.resize_to_target and min(img.size) > 240:
        ratio = max(.65, min(.92, math.sqrt(target / max(1, len(smallest))) * .96))
        new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
        if new_size == img.size:
            break
        progress(f'Otimizando resolução · {new_size[0]}×{new_size[1]}')
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        resized = True
        best, smallest = quality_search(img)
    dst.write_bytes(best if best is not None else smallest)
    if resized:
        return f'Meta agressiva: resolução ajustada de {original_size[0]}×{original_size[1]} para {img.width}×{img.height}, mantendo a proporção.'
    return 'Dimensões preservadas. Compressão com perdas; compare antes de usar.'


def document_compress(src, dst, options, event, progress):
    """Repack modern Office/OpenDocument containers and optimize embedded images."""
    image_prefixes = ('word/media/', 'ppt/media/', 'xl/media/', 'Pictures/')
    optimized = 0
    with zipfile.ZipFile(src, 'r') as source, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        entries = source.infolist()
        if any(info.filename.lower().startswith('_xmlsignatures/') or
               info.filename.lower() in {'meta-inf/documentsignatures.xml', 'meta-inf/macrosignatures.xml', 'meta-inf/signatures.xml'}
               for info in entries):
            raise ValueError('Documento com assinatura: preserve o documento original.')
        for position, info in enumerate(entries, 1):
            check_cancel(event)
            progress(f'Otimizando documento · {position}/{len(entries)}')
            data = source.read(info.filename)
            if info.filename.startswith(image_prefixes) and Path(info.filename).suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                try:
                    with Image.open(io.BytesIO(data)) as opened:
                        if getattr(opened, 'n_frames', 1) == 1:
                            image = opened.copy()
                            stream = io.BytesIO()
                            if opened.format == 'JPEG':
                                image.convert('RGB').save(stream, 'JPEG', quality=max(45, options.min_quality), optimize=True, progressive=True)
                            else:
                                image.save(stream, 'PNG', optimize=True)
                            candidate = stream.getvalue()
                            if len(candidate) < len(data):
                                data = candidate
                                optimized += 1
                except Exception:
                    pass
            output.writestr(info, data)
    return f'Documento recompactado. {optimized} imagem(ns) interna(s) otimizada(s), possivelmente com perdas. Propriedades e metadados do documento não são removidos.'


def pdf_compress(src, dst, options, target, event, progress):
    import pikepdf
    check_cancel(event)
    with pikepdf.open(src) as pdf:
        if pdf.is_encrypted:
            raise ValueError('PDF protegido: não é processado nesta versão.')
        if '/AcroForm' in pdf.Root and '/SigFlags' in pdf.Root.AcroForm:
            raise ValueError('PDF com assinatura: preserve o documento original.')
        if options.remove_metadata:
            if '/Metadata' in pdf.Root:
                del pdf.Root['/Metadata']
            for key in list(pdf.docinfo.keys()):
                del pdf.docinfo[key]
        pdf.save(dst, compress_streams=True, recompress_flate=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    check_cancel(event)
    structural_size = dst.stat().st_size
    if structural_size <= target or not options.flatten_pdf:
        return 'PDF otimizado estruturalmente, preservando texto selecionável e páginas.'

    # PDF files made mostly of vectors or already-compressed images often cannot
    # shrink structurally. Render a visual fallback only when the requested goal
    # needs it, keeping the smaller of the two candidates.
    document = None
    try:
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(str(src))
        quality_steps = list(range(82, max(24, options.min_quality) - 1, -14))
        scale_steps = (1.25, 1.0, .82) if options.reduction < 60 else (1.0, .82, .68)
        best_path = None
        best_size = structural_size
        for scale in scale_steps:
            for quality in quality_steps:
                check_cancel(event)
                progress(f'PDF · compactando páginas em alta fidelidade ({quality}%)…')
                images = []
                try:
                    for index in range(len(document)):
                        check_cancel(event)
                        page = document[index]
                        try:
                            bitmap = page.render(scale=scale)
                            try:
                                image = bitmap.to_pil().convert('RGB')
                            finally:
                                bitmap.close()
                        finally:
                            page.close()
                        images.append(image)
                    raster = dst.with_name(f'{dst.stem}-visual-{int(scale*100)}-{quality}.pdf')
                    images[0].save(raster, 'PDF', save_all=True, append_images=images[1:], quality=quality,
                                   resolution=72 * scale, optimize=True)
                    candidate_size = raster.stat().st_size
                    if candidate_size < best_size:
                        if best_path:
                            best_path.unlink(missing_ok=True)
                        best_path, best_size = raster, candidate_size
                    else:
                        raster.unlink(missing_ok=True)
                    if best_size <= target:
                        break
                finally:
                    for image in images:
                        image.close()
            if best_size <= target:
                break
        if best_path:
            dst.unlink(missing_ok=True)
            best_path.replace(dst)
            return 'PDF compactado visualmente para cumprir uma meta agressiva. Texto selecionável, links e formulários foram achatados.'
    except Cancelled:
        raise
    except Exception as error:
        # The structural result remains valid even if visual rendering is unavailable.
        return f'PDF otimizado estruturalmente; a compactação visual não foi aplicada ({error}).'
    finally:
        if document is not None:
            document.close()
    return 'PDF otimizado estruturalmente. O original já está próximo do menor tamanho possível sem alterar as páginas.'


def media_compress(src, dst, options, target, event, progress):
    ffmpeg, ffprobe = binary('ffmpeg'), binary('ffprobe')
    info = json.loads(run([ffprobe, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(src)], event, timeout=60))
    duration = float(info.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0 or options.start >= duration:
        raise ValueError('Duração inválida ou início além do fim do arquivo.')
    duration = min(duration-options.start, options.duration or duration)
    has_video = any(s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic') for s in info['streams'])
    has_audio = any(s.get('codec_type') == 'audio' for s in info['streams'])
    audio_only = options.action == 'Extrair áudio' or not has_video
    if audio_only and not has_audio:
        raise ValueError('Este arquivo não contém áudio.')
    base = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-ss', str(options.start), '-i', str(src), '-t', str(duration)]
    strip = ['-map_metadata', '-1', '-map_chapters', '-1'] if options.remove_metadata else []
    budget = int(target*8*.95/duration)
    if audio_only:
        bitrate = min(320_000, budget)
        if bitrate < 32_000:
            raise ValueError('Meta pequena demais para áudio. Aumente o tamanho máximo.')
        progress('Codificando áudio…')
        run(base+['-map', '0:a:0', '-vn', '-c:a', 'libmp3lame', '-b:a', str(bitrate)]+strip+[str(dst)], event)
        return 'MP3 com perdas; primeira faixa de áudio. Meta aproximada.'
    audio_rate = min(128_000, max(32_000, budget//5)) if has_audio else 0
    video_rate = budget-audio_rate
    if video_rate < 80_000:
        raise ValueError('Meta pequena demais para vídeo. Aumente o tamanho máximo ou recorte um trecho.')
    with tempfile.TemporaryDirectory(prefix='lynowcut-pass-') as tmp:
        common = base+['-map', '0:V:0', '-c:v', 'libx264', '-b:v', str(video_rate), '-preset', 'medium', '-pix_fmt', 'yuv420p', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-passlogfile', str(Path(tmp)/'pass')]
        progress('Vídeo · análise 1/2…')
        run(common+['-pass', '1', '-an', '-f', 'null', os.devnull], event)
        progress('Vídeo · codificação 2/2…')
        audio_args = ['-map', '0:a:0?', '-c:a', 'aac', '-b:a', str(audio_rate)] if has_audio else ['-an']
        run(common+['-pass', '2']+audio_args+strip+['-movflags', '+faststart', str(dst)], event)
    return 'MP4 H.264/AAC com perdas; primeira faixa de vídeo/áudio, sem legendas e anexos. Meta aproximada.'


def process(src: Path, folder: Path, options: Options, event=None, progress=lambda msg: None) -> Result:
    event = event or threading.Event()
    src = src.resolve(strict=True)
    before = src.stat().st_size
    if before == 0:
        raise ValueError('Arquivo vazio.')
    target = options.target(before)
    check_cancel(event)
    ext = src.suffix.lower()
    if options.action == 'Criar ZIP':
        suffix = '.zip'
    elif ext in IMAGES and options.action == 'Comprimir':
        suffix = {'WebP': '.webp', 'JPEG': '.jpg', 'PNG': '.png', 'AVIF': '.avif'}[options.image_format]
    elif ext == '.pdf' and options.action == 'Comprimir':
        suffix = '.pdf'
    elif ext in DOCUMENTS and options.action == 'Comprimir':
        suffix = ext
    elif ext in VIDEOS | AUDIO:
        suffix = '.mp3' if options.action == 'Extrair áudio' or ext in AUDIO else '.mp4'
    else:
        raise ValueError('Arquivo ou operação não compatível.')
    folder.mkdir(parents=True, exist_ok=True)
    # Candidate files live on the destination volume; publishing uses exclusive creation.
    with tempfile.TemporaryDirectory(prefix='.lynowcut-', dir=folder) as tmp:
        candidate = Path(tmp)/('candidate'+suffix)
        if options.action == 'Criar ZIP':
            with zipfile.ZipFile(candidate, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                with src.open('rb') as source, archive.open(src.name, 'w', force_zip64=True) as dest:
                    while chunk := source.read(1024*1024):
                        check_cancel(event)
                        dest.write(chunk)
            note = 'ZIP sem perdas. Arquivos já comprimidos podem não diminuir.'
        elif ext in IMAGES:
            note = image_compress(src, candidate, options, target, event, progress)
        elif ext == '.pdf':
            note = pdf_compress(src, candidate, options, target, event, progress)
        elif ext in DOCUMENTS:
            note = document_compress(src, candidate, options, event, progress)
        else:
            note = media_compress(src, candidate, options, target, event, progress)
        check_cancel(event)
        after = candidate.stat().st_size
        if after == 0:
            raise RuntimeError('O processamento produziu um arquivo vazio.')
        # Conversions, excerpts and archives may be useful even if larger.
        if after >= before and options.action == 'Comprimir' and options.start == 0 and options.duration is None:
            return Result(str(src), None, before, before, target, 'Sem ganho', 'Nenhuma cópia criada: resultado não ficou menor. '+note)
        n = 0
        while True:
            output = folder / f'{src.stem}-lynowcut{f"-{n}" if n else ""}{suffix}'
            try:
                handle = output.open('xb')
                break
            except FileExistsError:
                n += 1
        try:
            with handle, candidate.open('rb') as source:
                while chunk := source.read(1024*1024):
                    check_cancel(event)
                    handle.write(chunk)
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    return Result(str(src), str(output), before, after, target, 'Meta atingida' if after <= target else 'Meta não atingida', note)
