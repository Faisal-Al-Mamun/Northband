import type { ReactNode, SVGProps } from "react";

type Props = SVGProps<SVGSVGElement>;

function svg(props: Props, path: ReactNode) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true" {...props}>
      {path}
    </svg>
  );
}

export function IconHome(props: Props) {
  return svg(props, <path d="M4 10.8 12 4l8 6.8V20a1 1 0 0 1-1 1h-5.2v-6.2H10.2V21H5a1 1 0 0 1-1-1v-9.2Z" />);
}

export function IconWrite(props: Props) {
  return svg(
    props,
    <>
      <path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17v3Z" />
      <path d="m13.5 6.5 3 3" />
    </>,
  );
}

export function IconSpeak(props: Props) {
  return svg(
    props,
    <>
      <rect x="9" y="3.5" width="6" height="11" rx="3" />
      <path d="M6.5 11a5.5 5.5 0 0 0 11 0M12 16.5V20.5M8.5 20.5h7" />
    </>,
  );
}

export function IconAttempts(props: Props) {
  return svg(
    props,
    <>
      <path d="M6 6.5h12M6 12h12M6 17.5h8" />
    </>,
  );
}

export function IconProgress(props: Props) {
  return svg(props, <path d="M4 18V7.5M10 18v-6M16 18V5M22 18H2" />);
}

export function IconSettings(props: Props) {
  return svg(
    props,
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3.5v2.2M12 18.3V20.5M4.9 6.5l1.6 1.6M17.5 15.9l1.6 1.6M3.5 12h2.2M18.3 12H20.5M4.9 17.5l1.6-1.6M17.5 8.1l1.6-1.6" />
    </>,
  );
}

export function IconMic(props: Props) {
  return svg(
    props,
    <>
      <rect x="9" y="3.5" width="6" height="11" rx="3" />
      <path d="M6.5 11a5.5 5.5 0 0 0 11 0M12 16.5V20.5" />
    </>,
  );
}

export function IconRead(props: Props) {
  return svg(
    props,
    <>
      <path d="M4 5.5h7.2a2 2 0 0 1 2 2V20l-3.2-1.6L6.8 20V7.5a2 2 0 0 0-2-2Z" />
      <path d="M12.8 7.5a2 2 0 0 1 2-2H20V20l-3.2-1.6L13.6 20V7.5Z" />
    </>,
  );
}

export function IconListen(props: Props) {
  return svg(
    props,
    <>
      <path d="M4 12a8 8 0 0 1 16 0" />
      <path d="M8 12v3.5a2 2 0 0 0 2 2h1V12H8Zm8 0h-3v5.5h1a2 2 0 0 0 2-2V12Z" />
    </>,
  );
}

export function IconMock(props: Props) {
  return svg(
    props,
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5v5l3 2" />
    </>,
  );
}
