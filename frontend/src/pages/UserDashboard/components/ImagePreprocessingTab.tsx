import ImagePreprocessingWorkspace, {
  type PreprocessingSeedImage,
} from '../../../components/image-preprocessing/ImagePreprocessingWorkspace';

interface ImagePreprocessingTabProps {
  seedImage?: PreprocessingSeedImage | null;
  onUseInPredict?: (payload: { dataUrl: string; fileName: string }) => void;
}

export default function ImagePreprocessingTab({ seedImage, onUseInPredict }: ImagePreprocessingTabProps) {
  return (
    <ImagePreprocessingWorkspace
      title="图像预处理"
      uploadLabel="选择图像"
      enhancementTitle="高级效果"
      placeholderTitle="请上传图像开始处理"
      placeholderHint="支持 JPG、PNG、GIF 等常见图像格式。"
      downloadLabel="下载图像"
      useInPredictLabel="发送到预测评估"
      seedImage={seedImage}
      onUseInPredict={onUseInPredict}
    />
  );
}
