export interface ImageProcessingSettings {
  brightness: number;
  contrast: number;
  saturation: number;
  rotation: number;
  scale: number;
  blur: number;
  sharpen: number;
  invert: boolean;
  grayscale: number;
  edgeEnhance: number;
}

export const DEFAULT_IMAGE_PROCESSING_SETTINGS: ImageProcessingSettings = {
  brightness: 100,
  contrast: 100,
  saturation: 100,
  rotation: 0,
  scale: 100,
  blur: 0,
  sharpen: 0,
  invert: false,
  grayscale: 0,
  edgeEnhance: 0,
};

export function createDefaultImageProcessingSettings(): ImageProcessingSettings {
  return { ...DEFAULT_IMAGE_PROCESSING_SETTINGS };
}

export function readImageFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result);
        return;
      }

      reject(new Error('Unable to read image file.'));
    };

    reader.onerror = () => {
      reject(reader.error ?? new Error('Unable to read image file.'));
    };

    reader.readAsDataURL(file);
  });
}

export function dataUrlToFile(dataUrl: string, fileName: string): File {
  const [header, content = ''] = dataUrl.split(',');
  const mimeMatch = header.match(/data:(.*?);base64/);
  const mimeType = mimeMatch?.[1] ?? 'image/png';
  const binary = atob(content);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return new File([bytes], fileName, { type: mimeType });
}

export async function processImageDataUrl(
  source: string,
  settings: ImageProcessingSettings,
): Promise<string> {
  const image = await loadImage(source);
  const scaledWidth = Math.max(1, Math.round(image.width * (settings.scale / 100)));
  const scaledHeight = Math.max(1, Math.round(image.height * (settings.scale / 100)));
  const rotationRadians = (settings.rotation * Math.PI) / 180;
  const cos = Math.abs(Math.cos(rotationRadians));
  const sin = Math.abs(Math.sin(rotationRadians));
  const canvasWidth = Math.max(1, Math.round(scaledWidth * cos + scaledHeight * sin));
  const canvasHeight = Math.max(1, Math.round(scaledWidth * sin + scaledHeight * cos));

  const canvas = document.createElement('canvas');
  canvas.width = canvasWidth;
  canvas.height = canvasHeight;

  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Canvas rendering context is unavailable.');
  }

  context.clearRect(0, 0, canvasWidth, canvasHeight);
  context.save();
  context.translate(canvasWidth / 2, canvasHeight / 2);
  context.rotate(rotationRadians);
  context.filter = [
    `brightness(${settings.brightness}%)`,
    `contrast(${settings.contrast}%)`,
    `saturate(${settings.saturation}%)`,
    `blur(${settings.blur}px)`,
  ].join(' ');
  context.drawImage(image, -scaledWidth / 2, -scaledHeight / 2, scaledWidth, scaledHeight);
  context.restore();

  const imageData = context.getImageData(0, 0, canvasWidth, canvasHeight);
  applyChannelAdjustments(imageData.data, settings.grayscale, settings.invert);

  if (settings.sharpen > 0 || settings.edgeEnhance > 0) {
    const blurredImageData = buildBlurredImageData(canvas, canvasWidth, canvasHeight, settings);
    enhanceImageDetails(imageData.data, blurredImageData.data, settings);
  }

  context.putImageData(imageData, 0, 0);
  return canvas.toDataURL('image/png');
}

function loadImage(source: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();

    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('Unable to decode image.'));
    image.src = source;
  });
}

function applyChannelAdjustments(
  pixels: Uint8ClampedArray,
  grayscaleAmount: number,
  invert: boolean,
) {
  const grayscaleMix = Math.max(0, Math.min(1, grayscaleAmount / 100));

  for (let index = 0; index < pixels.length; index += 4) {
    let red = pixels[index];
    let green = pixels[index + 1];
    let blue = pixels[index + 2];

    if (grayscaleMix > 0) {
      const gray = 0.299 * red + 0.587 * green + 0.114 * blue;
      red = mixChannel(red, gray, grayscaleMix);
      green = mixChannel(green, gray, grayscaleMix);
      blue = mixChannel(blue, gray, grayscaleMix);
    }

    if (invert) {
      red = 255 - red;
      green = 255 - green;
      blue = 255 - blue;
    }

    pixels[index] = red;
    pixels[index + 1] = green;
    pixels[index + 2] = blue;
  }
}

function buildBlurredImageData(
  sourceCanvas: HTMLCanvasElement,
  width: number,
  height: number,
  settings: ImageProcessingSettings,
): ImageData {
  const blurCanvas = document.createElement('canvas');
  blurCanvas.width = width;
  blurCanvas.height = height;

  const blurContext = blurCanvas.getContext('2d');
  if (!blurContext) {
    throw new Error('Canvas rendering context is unavailable.');
  }

  const blurRadius = Math.max(1.2, Math.min(6, 1.2 + Math.max(settings.sharpen, settings.edgeEnhance) * 0.35));

  blurContext.clearRect(0, 0, width, height);
  blurContext.filter = `blur(${blurRadius}px)`;
  blurContext.drawImage(sourceCanvas, 0, 0, width, height);

  return blurContext.getImageData(0, 0, width, height);
}

function enhanceImageDetails(
  pixels: Uint8ClampedArray,
  blurredPixels: Uint8ClampedArray,
  settings: ImageProcessingSettings,
) {
  const sharpenStrength = Math.max(0, settings.sharpen) / 10;
  const edgeStrength = Math.max(0, settings.edgeEnhance) / 10;
  const threshold = 2 + sharpenStrength * 10;

  for (let index = 0; index < pixels.length; index += 4) {
    for (let channel = 0; channel < 3; channel += 1) {
      const baseValue = pixels[index + channel];
      const blurredValue = blurredPixels[index + channel];
      const detail = baseValue - blurredValue;
      let nextValue = baseValue;

      if (sharpenStrength > 0 && Math.abs(detail) >= threshold) {
        nextValue += detail * (0.55 + sharpenStrength * 1.25);
      }

      if (edgeStrength > 0) {
        nextValue += Math.abs(detail) * (0.18 + edgeStrength * 0.65);
      }

      pixels[index + channel] = clamp(nextValue);
    }
  }
}

function mixChannel(base: number, target: number, amount: number): number {
  return clamp(base + (target - base) * amount);
}

function clamp(value: number): number {
  return Math.min(255, Math.max(0, Math.round(value)));
}
