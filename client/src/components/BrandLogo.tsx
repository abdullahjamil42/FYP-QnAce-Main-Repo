import Image from "next/image";

type BrandLogoProps = {
  className?: string;
};

export default function BrandLogo({ className }: BrandLogoProps) {
  return (
    <Image
      src="/QnAce-logo.png"
      alt="QnAce logo"
      width={382}
      height={232}
      className={className}
      priority
    />
  );
}
