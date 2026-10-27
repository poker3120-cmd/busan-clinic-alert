/* 검사 주제별 로컬 의료 개념도
   외부 이미지 요청 없이 브라우저에서 SVG를 생성합니다.
   임상 사진이나 진단용 이미지를 대체하지 않는 설명용 도식입니다. */

const TOPICS = [
  {
    key: "artery",
    label: "동맥·혈관",
    match: /동맥경화|죽상경화|혈관|심혈관|관상동맥|혈류|혈전|말초혈관/i,
    svg: `
      <g transform="translate(0 0)">
        <path d="M58 190 C185 138 294 158 401 182 S624 210 742 165 L742 315 C620 363 512 334 401 309 S181 289 58 330Z" fill="#a82a43" opacity=".94"/>
        <path d="M58 205 C178 168 286 184 400 204 S621 231 742 188 L742 292 C624 332 513 309 400 289 S180 276 58 313Z" fill="#f08b99"/>
        <path d="M58 226 C176 194 286 210 400 227 S626 252 742 211 L742 269 C621 301 515 284 400 267 S178 248 58 290Z" fill="#fff0ed"/>
        <path d="M335 199 C385 205 403 217 436 219 C462 220 473 206 506 211 C539 216 550 236 578 237 L585 282 C547 278 520 260 493 263 C458 268 443 287 411 276 C383 266 364 241 335 239Z" fill="#f1c75b" stroke="#d69730" stroke-width="4"/>
        <path d="M82 243 C99 235 110 237 123 245 M144 231 C159 226 174 227 187 235 M222 239 C237 236 248 238 261 244 M609 250 C625 246 640 244 654 246" fill="none" stroke="#f8b2ba" stroke-width="5" stroke-linecap="round"/>
        <g fill="#c94358" stroke="#f3a2ad" stroke-width="3">
          <ellipse cx="147" cy="258" rx="16" ry="8" transform="rotate(-9 147 258)"/>
          <ellipse cx="245" cy="257" rx="16" ry="8" transform="rotate(7 245 257)"/>
          <ellipse cx="304" cy="251" rx="16" ry="8" transform="rotate(-4 304 251)"/>
          <ellipse cx="628" cy="260" rx="16" ry="8" transform="rotate(8 628 260)"/>
          <ellipse cx="682" cy="248" rx="16" ry="8" transform="rotate(-7 682 248)"/>
        </g>
        <path d="M474 143 L474 187" stroke="#b27b25" stroke-width="3" stroke-linecap="round"/>
        <circle cx="474" cy="135" r="7" fill="#f1c75b"/>
        <path d="M472 126 L450 108" stroke="#b27b25" stroke-width="2" stroke-linecap="round"/>
      </g>`
  },
  {
    key: "liver",
    label: "간",
    match: /간암|간염|간기능|간섬유화|간질환|간세포|간경변|간암위험도/i,
    svg: `
      <g transform="translate(0 4)">
        <path d="M139 239 C161 160 267 111 391 128 C451 136 487 166 534 164 C588 162 623 142 667 165 C711 188 699 256 658 293 C622 326 548 345 467 332 C403 322 359 296 302 303 C237 311 174 300 145 273 C135 264 133 251 139 239Z" fill="url(#organ)" stroke="#a8354b" stroke-width="7"/>
        <path d="M404 137 C422 181 423 231 401 287" fill="none" stroke="#eaa0a8" stroke-width="8" stroke-linecap="round" opacity=".85"/>
        <path d="M403 217 C454 213 499 231 539 268" fill="none" stroke="#9e3047" stroke-width="7" stroke-linecap="round" opacity=".8"/>
        <path d="M402 218 C360 204 330 181 312 154" fill="none" stroke="#9e3047" stroke-width="7" stroke-linecap="round" opacity=".8"/>
        <g fill="#f5c6a6" opacity=".95"><circle cx="268" cy="198" r="8"/><circle cx="288" cy="220" r="5"/><circle cx="345" cy="249" r="7"/><circle cx="476" cy="183" r="6"/><circle cx="520" cy="216" r="8"/><circle cx="590" cy="246" r="6"/></g>
      </g>`
  },
  {
    key: "heart",
    label: "심장",
    match: /심장|심근|심부전|심전도|심혈관|관상동맥|심장질환/i,
    svg: `
      <g transform="translate(0 -4)">
        <path d="M401 335 C359 294 235 223 236 165 C237 113 294 93 337 121 C364 139 382 160 401 181 C421 156 445 126 477 117 C525 104 568 139 563 183 C557 239 450 306 401 335Z" fill="url(#organ)" stroke="#a62843" stroke-width="7"/>
        <path d="M391 170 C366 143 360 109 378 87 C393 70 416 78 423 101 C431 127 414 152 401 181" fill="none" stroke="#b72c49" stroke-width="21" stroke-linecap="round"/>
        <path d="M425 145 C448 118 464 85 458 58" fill="none" stroke="#b72c49" stroke-width="18" stroke-linecap="round"/>
        <path d="M386 186 C352 208 333 235 322 265 M416 192 C446 218 457 244 465 272" fill="none" stroke="#f7bac1" stroke-width="9" stroke-linecap="round"/>
        <path d="M330 176 C350 183 366 199 379 220 M475 171 C457 190 443 207 432 226" fill="none" stroke="#f7bac1" stroke-width="8" stroke-linecap="round"/>
      </g>`
  },
  {
    key: "lung",
    label: "폐",
    match: /폐암|폐기능|폐질환|호흡기|기관지|폐렴|폐결절/i,
    svg: `
      <g fill="url(#organ)" stroke="#a83a57" stroke-width="6" stroke-linejoin="round">
        <path d="M385 125 L385 208 C354 204 334 180 316 165 C291 149 275 173 262 201 C243 243 225 296 251 320 C278 345 329 319 361 291 C387 267 393 230 393 202 L393 126Z"/>
        <path d="M415 125 L415 208 C446 204 466 180 484 165 C509 149 525 173 538 201 C557 243 575 296 549 320 C522 345 471 319 439 291 C413 267 407 230 407 202 L407 126Z"/>
      </g>
      <path d="M400 91 L400 210 M400 153 L350 196 M400 153 L450 196 M350 196 L320 238 M450 196 L480 238" fill="none" stroke="#b63c55" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M400 92 L400 210 M400 153 L350 196 M400 153 L450 196 M350 196 L320 238 M450 196 L480 238" fill="none" stroke="#f9d9d9" stroke-width="5" stroke-linecap="round"/>
    `
  },
  {
    key: "brain",
    label: "뇌",
    match: /뇌혈관|뇌졸중|치매|알츠하이머|인지기능|뇌기능|신경퇴행|뇌질환/i,
    svg: `
      <path d="M398 111 C373 77 323 84 309 117 C272 106 247 139 258 170 C224 195 241 236 267 250 C258 288 294 314 325 296 C348 323 380 306 398 286 C416 306 448 323 471 296 C502 314 538 288 529 250 C555 236 572 195 538 170 C549 139 524 106 487 117 C473 84 423 77 398 111Z" fill="url(#organ)" stroke="#ad5562" stroke-width="6"/>
      <path d="M398 110 L398 286 M315 131 C344 143 341 165 324 178 M277 183 C305 186 311 206 295 222 M313 270 C337 254 355 267 353 292 M475 131 C450 143 455 165 472 178 M519 183 C491 186 485 206 501 222 M483 270 C459 254 441 267 443 292 M348 111 C368 125 360 143 346 151 M448 111 C428 125 436 143 450 151" fill="none" stroke="#fbe5de" stroke-width="7" stroke-linecap="round"/>
    `
  },
  {
    key: "kidney",
    label: "신장",
    match: /신장|콩팥|신부전|신기능|요로|단백뇨|신장질환/i,
    svg: `
      <path d="M330 112 C275 93 236 143 241 207 C245 268 284 311 328 294 C365 280 361 240 340 218 C317 194 318 169 344 149 C359 137 350 119 330 112Z" fill="url(#organ)" stroke="#a63a54" stroke-width="7"/>
      <path d="M470 112 C525 93 564 143 559 207 C555 268 516 311 472 294 C435 280 439 240 460 218 C483 194 482 169 456 149 C441 137 450 119 470 112Z" fill="url(#organ)" stroke="#a63a54" stroke-width="7"/>
      <path d="M330 195 C369 198 375 231 399 246 C423 231 429 198 470 195" fill="none" stroke="#e4ac66" stroke-width="13" stroke-linecap="round"/>
      <path d="M330 195 C362 203 372 254 383 284 M470 195 C438 203 428 254 417 284" fill="none" stroke="#d1a45c" stroke-width="8" stroke-linecap="round"/>
    `
  },
  {
    key: "thyroid",
    label: "갑상선",
    match: /갑상선|갑상샘|티록신|갑상선호르몬/i,
    svg: `
      <g fill="url(#organ)" stroke="#ad3f5b" stroke-width="7">
        <path d="M374 163 C340 116 299 145 301 196 C302 238 329 269 363 256 C389 246 387 208 374 163Z"/>
        <path d="M426 163 C460 116 501 145 499 196 C498 238 471 269 437 256 C411 246 413 208 426 163Z"/>
      </g>
      <path d="M400 132 L400 330" stroke="#c8a6a3" stroke-width="32" stroke-linecap="round"/>
      <path d="M400 132 L400 330" stroke="#f6d9d7" stroke-width="20" stroke-linecap="round"/>
      <path d="M386 184 L414 184 M386 213 L414 213 M386 242 L414 242 M386 271 L414 271 M386 300 L414 300" stroke="#c89a9c" stroke-width="5" stroke-linecap="round"/>
    `
  },
  {
    key: "cell",
    label: "세포",
    match: /암|종양|유전자|분자|세포|바이러스|감염|면역|염증|종양표지자|마커|유전/i,
    svg: `
      <g stroke-width="5">
        <circle cx="298" cy="183" r="75" fill="#f3b2bd" stroke="#c85f7a"/>
        <circle cx="298" cy="183" r="27" fill="#a94772"/><circle cx="285" cy="168" r="8" fill="#fbe4e8"/>
        <circle cx="478" cy="245" r="91" fill="#f6d9a8" stroke="#d7a454"/>
        <circle cx="478" cy="245" r="34" fill="#c77b4d"/><circle cx="466" cy="232" r="10" fill="#fff0d0"/>
        <circle cx="447" cy="125" r="39" fill="#d5c9ee" stroke="#8f80c0"/>
        <circle cx="447" cy="125" r="14" fill="#7866a7"/>
        <circle cx="267" cy="287" r="25" fill="#c7e4e1" stroke="#6aaaa8"/>
        <circle cx="267" cy="287" r="8" fill="#4e8e92"/>
      </g>
      <g fill="none" stroke="#c77c91" stroke-width="3" opacity=".8"><path d="M240 140 L258 155 L244 174 M336 193 L354 209 L344 228 M432 274 L413 293 L424 310 M514 198 L538 185 L548 205"/></g>
    `
  },
  {
    key: "blood",
    label: "혈액",
    match: /혈액|혈구|빈혈|응고|혈소판|백혈구|적혈구|혈당|당뇨|인슐린|대사/i,
    svg: `
      <g>
        <g fill="#c9415a" stroke="#a72a43" stroke-width="5">
          <ellipse cx="269" cy="181" rx="52" ry="29" transform="rotate(-22 269 181)"/><ellipse cx="420" cy="141" rx="48" ry="27" transform="rotate(18 420 141)"/><ellipse cx="534" cy="238" rx="55" ry="30" transform="rotate(-14 534 238)"/><ellipse cx="353" cy="283" rx="49" ry="28" transform="rotate(20 353 283)"/>
        </g>
        <g fill="#eea0ac" opacity=".9">
          <ellipse cx="269" cy="181" rx="29" ry="13" transform="rotate(-22 269 181)"/><ellipse cx="420" cy="141" rx="27" ry="12" transform="rotate(18 420 141)"/><ellipse cx="534" cy="238" rx="31" ry="14" transform="rotate(-14 534 238)"/><ellipse cx="353" cy="283" rx="27" ry="13" transform="rotate(20 353 283)"/>
        </g>
        <g fill="#d5c9ee" stroke="#8f80c0" stroke-width="5"><circle cx="366" cy="209" r="31"/><circle cx="464" cy="322" r="21"/></g>
        <g fill="#f3d179" stroke="#cba447" stroke-width="3"><circle cx="596" cy="150" r="10"/><circle cx="214" cy="274" r="8"/><circle cx="451" cy="194" r="9"/><circle cx="590" cy="319" r="9"/></g>
      </g>
    `
  },
];

function frame(inner) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480" viewBox="0 0 800 480">
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff8f7"/><stop offset="1" stop-color="#f8e3e5"/></linearGradient>
      <linearGradient id="organ" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#dc7788"/><stop offset=".55" stop-color="#c34b65"/><stop offset="1" stop-color="#97304b"/></linearGradient>
      <radialGradient id="glow"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset="1" stop-color="#f7dfe2" stop-opacity=".08"/></radialGradient>
    </defs>
    <rect width="800" height="480" rx="34" fill="url(#bg)"/>
    <circle cx="105" cy="82" r="116" fill="#fff" opacity=".36"/>
    <circle cx="693" cy="408" r="162" fill="url(#glow)"/>
    <path d="M42 392 C160 349 229 426 347 387 S579 344 758 405" fill="none" stroke="#fff" stroke-width="3" opacity=".68"/>
    <g opacity=".28" fill="#dbaab2"><circle cx="93" cy="350" r="5"/><circle cx="121" cy="367" r="3"/><circle cx="706" cy="111" r="5"/><circle cx="683" cy="91" r="3"/><circle cx="649" cy="373" r="4"/></g>
    ${inner}
  </svg>`;
}

function encodeSvg(svg) {
  return "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg);
}

export function createMedicalIllustration(sourceText = "") {
  const text = String(sourceText || "");
  const topic = TOPICS.find((candidate) => candidate.match.test(text)) || {
    key: "clinical",
    label: "검사 원리",
    svg: `
      <g fill="none" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
        <path d="M226 257 C255 182 318 151 369 190 S452 292 503 222 S571 151 601 196" stroke="#c55069"/>
        <path d="M223 286 C268 312 307 309 342 274 S411 181 448 219 S517 308 578 269" stroke="#df9b54"/>
      </g>
      <g fill="#fff" stroke-width="6"><circle cx="232" cy="257" r="29" stroke="#c55069"/><circle cx="369" cy="190" r="29" stroke="#c55069"/><circle cx="503" cy="222" r="29" stroke="#c55069"/><circle cx="601" cy="196" r="29" stroke="#c55069"/></g>
      <g fill="#c55069"><circle cx="232" cy="257" r="9"/><circle cx="369" cy="190" r="9"/><circle cx="503" cy="222" r="9"/><circle cx="601" cy="196" r="9"/></g>
    `
  };
  const safeKey = topic.key.replace(/[^a-z0-9-]/gi, "-");
  return {
    id: "medical-auto-" + safeKey,
    name: topic.label + " 개념도(설명용 일러스트)",
    source: "자동 생성 의료 개념도",
    dataUrl: encodeSvg(frame(topic.svg)),
    width: 800,
    height: 480,
    generated: true,
    topicKey: safeKey,
  };
}
