type BrandLogoProps = {
  className?: string;
};

export default function BrandLogo({ className }: BrandLogoProps) {
  return (
    <svg
      viewBox="0 0 382 232"
      className={className}
      aria-hidden="true"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M217 22h94c48.6 0 88 39.4 88 88v28.5c0 48.6-39.4 88-88 88h-15.8l-31.8 30.6c-11 10.6-29.4 2.8-29.4-12.5V226h-17c-9.9 0-18-8.1-18-18V40c0-9.9 8.1-18 18-18Z"
        fill="currentColor"
      />
      <path
        d="M137.5 24c32.8 0 61.1 20.8 71.9 50.5 22.7 8.6 39.6 30.4 39.6 56.6 0 33.8-27.5 61.3-61.3 61.3H74.5c-40 0-72.5-32.5-72.5-72.5 0-35.7 25.8-65.7 60-72.2C73.8 33.8 97.7 24 124.6 24h12.9Z"
        stroke="currentColor"
        strokeWidth="12"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M174 34v149" stroke="currentColor" strokeWidth="12" strokeLinecap="round" />
      <circle cx="77" cy="89" r="11" fill="currentColor" />
      <circle cx="116" cy="62" r="11" fill="currentColor" />
      <circle cx="155" cy="90" r="11" fill="currentColor" />
      <circle cx="86" cy="132" r="11" fill="currentColor" />
      <circle cx="125" cy="157" r="11" fill="currentColor" />
      <circle cx="155" cy="133" r="11" fill="currentColor" />
      <path d="M88 89h24" stroke="currentColor" strokeWidth="8" strokeLinecap="round" />
      <path d="M124 68l22 16" stroke="currentColor" strokeWidth="8" strokeLinecap="round" />
      <path d="M95 124l20-52" stroke="currentColor" strokeWidth="8" strokeLinecap="round" />
      <path d="M97 132h20" stroke="currentColor" strokeWidth="8" strokeLinecap="round" />
      <path d="M125 150l21-14" stroke="currentColor" strokeWidth="8" strokeLinecap="round" />
      <path d="M155 123V97" stroke="currentColor" strokeWidth="8" strokeLinecap="round" />
    </svg>
  );
}
