/** Achica la foto de la planilla (lado mayor 1800 px, JPEG): ocupa menos en el celular y al sincronizar. */
export async function shrinkImage(file: File, maxSide = 1800): Promise<Blob> {
  try {
    const bmp = await createImageBitmap(file)
    const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height))
    if (scale === 1 && file.size < 1_500_000) return file
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bmp.width * scale)
    canvas.height = Math.round(bmp.height * scale)
    canvas.getContext('2d')!.drawImage(bmp, 0, 0, canvas.width, canvas.height)
    const out = await new Promise<Blob | null>((r) => canvas.toBlob(r, 'image/jpeg', 0.85))
    return out && out.size < file.size ? out : file
  } catch {
    return file // formato que el navegador no decodifica: se envía tal cual
  }
}
