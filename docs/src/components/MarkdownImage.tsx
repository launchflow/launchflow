import Image from 'next/image'

export function MarkdownImage({
  src,
  alt,
  className,
  height = 800,
  width = 800,
}: {
  src: string
  alt: string
  className: string
  height: number
  width: number
}) {
  return (
    <div className='flex justify-center items-center'>
      <Image
        src={src}
        alt={alt}
        className={className}
        width={width}
        height={height}
      />
    </div>
  )
}
