export default function NoirSpider() {
  return (
    <div className="spider" aria-hidden="true">
      <svg viewBox="0 0 160 260" width="120" height="195" xmlns="http://www.w3.org/2000/svg">
        <line x1="80" y1="0" x2="80" y2="92" stroke="#cfcac0" strokeWidth="1.5" />
        <g stroke="#0a0a0a" strokeWidth="3.5" strokeLinecap="round" fill="none">
          <path d="M62 150 Q30 140 18 168 Q12 182 20 196" />
          <path d="M62 162 Q26 160 16 190 Q12 206 22 218" />
          <path d="M64 174 Q34 182 30 208 Q28 224 38 234" />
          <path d="M70 184 Q52 200 54 226 Q56 240 66 246" />
          <path d="M98 150 Q130 140 142 168 Q148 182 140 196" />
          <path d="M98 162 Q134 160 144 190 Q148 206 138 218" />
          <path d="M96 174 Q126 182 130 208 Q132 224 122 234" />
          <path d="M90 184 Q108 200 106 226 Q104 240 94 246" />
        </g>
        <ellipse cx="80" cy="168" rx="26" ry="38" fill="#0a0a0a" stroke="#cfcac0" strokeWidth="1" />
        <path d="M80 138 L80 196" stroke="#cfcac0" strokeWidth="1" opacity=".5" />
        <circle cx="80" cy="120" r="22" fill="#0a0a0a" stroke="#cfcac0" strokeWidth="1" />
        <circle cx="72" cy="124" r="4" fill="#f1efe9" />
        <circle cx="88" cy="124" r="4" fill="#f1efe9" />
        <g transform="rotate(180 80 100)">
          <ellipse cx="80" cy="98" rx="34" ry="7" fill="#0a0a0a" stroke="#cfcac0" strokeWidth="1" />
          <path d="M60 98 Q60 74 80 74 Q100 74 100 98 Z" fill="#0a0a0a" stroke="#cfcac0" strokeWidth="1" />
          <rect x="61" y="90" width="38" height="6" fill="#f1efe9" />
        </g>
      </svg>
    </div>
  );
}