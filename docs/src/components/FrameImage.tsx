export function FrameImage({
  src,
  alt,
  height,
  width,
}: {
  src: string
  alt: string
  height?: number
  width?: number
}) {
  return (
    <div className="flex justify-center">
      <img
        style={{
          width: width ? `${width}px` : 'auto',
          height: height ? `${height}px` : 'auto',
        }}
        className="h-[${height}px] rounded-lg border-2 border-gray-300 p-1"
        src={src}
        alt={alt}
        height={height}
      />
    </div>
  )
}
