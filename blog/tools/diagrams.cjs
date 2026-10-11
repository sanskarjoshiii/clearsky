// Excalidraw diagrams for the blog, written as Excalidraw "skeleton" elements.
// render-diagrams.cjs turns them into real Excalidraw scenes (.excalidraw) and PNGs.
// Arrows are routed here (edge to edge), so they never depend on Excalidraw's auto-binding.
const fs = require("node:fs");
const path = require("node:path");

const ICONS = "D:/clearsky-blog/node_modules/aws-icons/icons/architecture-service";
const FONT = 5; // Excalifont (hand-drawn)
const INK = "#1e1e1e";
const MUTED = "#5c5f66";
const BG = {
  yellow: "#fff3bf", violet: "#e5dbff", blue: "#d0ebff", gray: "#f1f3f5", green: "#d3f9d8",
  teal: "#c3fae8", orange: "#ffe8cc", red: "#ffe3e3", white: "#ffffff",
};

let REG = {}; // id -> {x, y, w, h} of every box in the current diagram

const T = (x, y, text, size = 20, color = INK, extra = {}) => ({ type: "text", x, y, text, fontSize: size, fontFamily: FONT, strokeColor: color, ...extra });

function box(id, x, y, w, h, text, bg, size = 20, extra = {}, label = {}) {
  REG[id] = { x, y, w, h };
  return {
    type: "rectangle", id, x, y, width: w, height: h, backgroundColor: bg, fillStyle: "solid", strokeColor: INK,
    strokeWidth: 2, roughness: 1, roundness: { type: 3 },
    ...(text ? { label: { text, fontSize: size, fontFamily: FONT, strokeColor: INK, ...label } } : {}), ...extra,
  };
}

/** Straight arrow from the edge of `from` to the edge of `to`. `shift` moves it sideways (two-way pairs). */
function arrow(from, to, label, extra = {}, shift = 0) {
  const a = REG[from], b = REG[to];
  if (!a || !b) throw new Error(`arrow ${from}->${to}: unknown box`);
  const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 }, bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
  const dx = bc.x - ac.x, dy = bc.y - ac.y, gap = 8;
  let s, e;
  if (Math.abs(dx) * a.h > Math.abs(dy) * a.w) {
    s = { x: dx > 0 ? a.x + a.w + gap : a.x - gap, y: ac.y + shift };
    e = { x: dx > 0 ? b.x - gap : b.x + b.w + gap, y: bc.y + shift };
  } else {
    s = { x: ac.x + shift, y: dy > 0 ? a.y + a.h + gap : a.y - gap };
    e = { x: bc.x + shift, y: dy > 0 ? b.y - gap : b.y + b.h + gap };
  }
  return {
    type: "arrow", x: s.x, y: s.y, width: Math.abs(e.x - s.x), height: Math.abs(e.y - s.y),
    points: [[0, 0], [e.x - s.x, e.y - s.y]], strokeColor: INK, strokeWidth: 2, roughness: 1, endArrowhead: "arrow",
    ...(label ? { label: { text: label, fontSize: 16, fontFamily: FONT, strokeColor: MUTED } } : {}), ...extra,
  };
}

function iconFile(name) {
  const svg = fs.readFileSync(path.join(ICONS, `${name}.svg`));
  // rasterised to PNG by render-diagrams.cjs (Excalidraw drops parts of embedded SVGs)
  return { id: name, mimeType: "image/svg+xml", dataURL: "data:image/svg+xml;base64," + svg.toString("base64"), created: 1 };
}

/** An AWS service card: official icon at the top, name at the bottom. */
function service(id, x, y, icon, name, files, w = 170) {
  files[icon] = iconFile(icon);
  return [
    box(id, x, y, w, 132, name, BG.white, 17, { strokeColor: "#ced4da", strokeWidth: 1 }, { verticalAlign: "bottom" }),
    { type: "image", x: x + w / 2 - 28, y: y + 10, width: 56, height: 56, fileId: icon, status: "saved" },
  ];
}

// ---------------------------------------------------------------- 1. the 3 pm gap
function gap() {
  REG = {};
  const X = (h) => 70 + (h - 9) * 105;
  const els = [
    T(0, 0, "The satellite looks at lunchtime. The fires start after 3 pm.", 34),
    { type: "arrow", x: X(9) - 20, y: 400, width: X(20) - X(9) + 70, height: 0, points: [[0, 0], [X(20) - X(9) + 70, 0]], strokeColor: INK, strokeWidth: 2, endArrowhead: "arrow" },
  ];
  for (let h = 9; h <= 20; h++) {
    els.push({ type: "line", x: X(h), y: 392, width: 0, height: 16, points: [[0, 0], [0, 16]], strokeColor: INK, strokeWidth: 2 });
    els.push(T(X(h) - 18, 416, h === 12 ? "noon" : h < 12 ? `${h} am` : `${h - 12} pm`, 17, MUTED));
  }
  els.push(
    box("sat", X(10.5), 150, X(13.5) - X(10.5), 230, "🛰️ Satellites pass\n10:30 am to 1:30 pm", BG.blue, 22),
    box("fire", X(15), 150, X(20) - X(15), 230, "🔥 Over 90% of large fires\nin Punjab were lit after 3 pm\n(2024 and 2025)", BG.red, 22),
    T(X(9), 470, "In 2021 that share was only 3%. The fires did not stop: they moved to the evening,\nout of the satellites' view.", 20),
    T(X(9), 540, "Source: iFOREST Stubble Burning Status Report 2025, via The Tribune (9 Dec 2025)", 16, MUTED),
  );
  return { elements: els, files: {} };
}

// ---------------------------------------------------------------- 2. one voice note, start to finish
function flow() {
  REG = {};
  const W = 270, H = 140, top = 110, low = 400, xs = [0, 420, 840, 1260];
  const els = [
    T(0, 0, "One voice note, start to finish", 34),
    box("n1", xs[0], top, W, H, "🎙️ Farmer\nsends one WhatsApp\nvoice note or text", BG.yellow),
    box("n2", xs[1], top, W, H, "🤖 AI agent\nname · village · acres\n· harvest date", BG.violet),
    box("n3", xs[2], top, W, H, "🧭 Matcher\nnearest free baler\n+ best-paying buyer", BG.blue),
    box("n4", xs[3], top, W, H, "📨 Offer to the baler\nday reserved, farmer\ntold \"request sent\"", BG.gray),
    box("n5", xs[3], low, W, H, "✅ Baler accepts\nonly now the farmer\ngets the confirmation", BG.green),
    box("n6", xs[2], low, W, H, "🚜 Pickup day\nbaler taps Done,\nfield is cleared", BG.green),
    box("n7", xs[1], low, W, H, "🏭 Straw to industry\nthe buyer receives\nthe bales", BG.teal),
    box("n8", xs[0], low, W, H, "📊 Impact counted\nstraw that was\nnot burnt", BG.orange),
  ];
  els.push(
    arrow("n1", "n2", "Transcribe"), arrow("n2", "n3", "tools"), arrow("n3", "n4", "1 transaction"),
    arrow("n4", "n5", "Accept"), arrow("n5", "n6"), arrow("n6", "n7"), arrow("n7", "n8"),
  );
  return { elements: els, files: {} };
}

// ---------------------------------------------------------------- 3. the offer lifecycle
function offer() {
  REG = {};
  const els = [
    T(0, -20, "A booking is a question until a baler says yes", 34),
    box("new", 0, 140, 210, 110, "Farmer\nbooks", BG.yellow, 22),
    box("off", 320, 130, 280, 130, "OFFERED\nbaler-day reserved", BG.gray, 22),
    box("con", 780, 130, 280, 130, "CONFIRMED\non the baler's route", BG.green, 22),
    box("done", 1220, 130, 250, 130, "DONE\nfield cleared", BG.teal, 22),
    box("next", 320, 430, 280, 130, "Next-best baler\n(never the one\nwho refused)", BG.blue, 20),
    box("esc", 780, 430, 320, 130, "After 3 balers:\nofficer's radar shows\n\"no baler accepted\"", BG.red, 20),
  ];
  els.push(
    arrow("new", "off"), arrow("off", "con", "Accept"), arrow("con", "done", "Done"),
    arrow("off", "next", "Decline or 2 h\nno answer", {}, -60),
    arrow("next", "off", "offer again", { strokeStyle: "dashed" }, 60),
    arrow("next", "esc"),
    T(320, 92, "farmer: 📨 \"request sent\"", 18, MUTED),
    T(780, 92, "farmer: ✅ confirmed + baler's name", 18, MUTED),
    T(1220, 92, "farmer: \"field cleared\"", 18, MUTED),
    T(780, 580, "farmer is told an officer will follow up", 18, MUTED),
  );
  return { elements: els, files: {} };
}

// ---------------------------------------------------------------- 4. AWS architecture
function architecture() {
  REG = {};
  const files = {};
  const els = [T(0, 0, "clearsky on AWS: fully serverless", 34)];
  const G = (x, y, w, h, title) => [
    { type: "rectangle", x, y, width: w, height: h, strokeColor: "#adb5bd", strokeStyle: "dashed", strokeWidth: 1, roughness: 1, roundness: { type: 3 }, backgroundColor: "transparent" },
    T(x + 14, y + 10, title, 20, MUTED),
  ];
  els.push(...G(-20, 70, 1720, 470, "Farmer path: WhatsApp"));
  els.push(...G(-20, 570, 1210, 230, "Dashboards: officer · baler · buyer"));
  els.push(...G(-20, 830, 1210, 230, "Clocks: every hour · every 15 min · 6 pm IST"));
  els.push(...G(1220, 570, 480, 490, "Operations"));

  // farmer path
  els.push(box("farmer", 0, 130, 170, 132, "👨‍🌾 Farmer\nvoice or text", BG.yellow, 18));
  els.push(box("meta", 230, 130, 170, 132, "WhatsApp\nCloud API\n(Meta)", BG.green, 18));
  els.push(...service("apigw", 460, 130, "AmazonAPIGateway", "API Gateway\nHTTP API", files));
  els.push(...service("hook", 690, 130, "AWSLambda", "Lambda\nwebhook", files));
  els.push(...service("sqs", 920, 130, "AmazonSimpleQueueService", "SQS + DLQ", files));
  els.push(...service("proc", 1150, 130, "AWSLambda", "Lambda\nAI agent (Strands)", files, 190));
  els.push(...service("ddb", 1470, 130, "AmazonDynamoDB", "DynamoDB\n12 tables", files));
  els.push(...service("s3m", 920, 370, "AmazonSimpleStorageService", "S3\nvoice files", files));
  els.push(...service("tr", 1150, 370, "AmazonTranscribe", "Transcribe\nvoice to text", files, 190));
  els.push(...service("po", 1400, 370, "AmazonPolly", "Polly\nHindi voice", files, 190));
  els.push(
    arrow("farmer", "meta"), arrow("meta", "apigw"), arrow("apigw", "hook"), arrow("hook", "sqs"),
    arrow("sqs", "proc"), arrow("proc", "ddb", "book"), arrow("proc", "s3m"), arrow("proc", "tr"), arrow("proc", "po"),
  );

  // dashboards
  els.push(box("users", 0, 625, 160, 132, "👩‍💼 🚜 🏭\nbrowser\nor phone", BG.yellow, 18));
  els.push(...service("cf", 200, 625, "AmazonCloudFront", "CloudFront + S3\nACM certificate", files, 180));
  els.push(...service("cog", 420, 625, "AmazonCognito", "Cognito\nsign-in, roles", files, 160));
  els.push(...service("apigw2", 620, 625, "AmazonAPIGateway", "API Gateway\nJWT check", files, 160));
  els.push(...service("api", 820, 625, "AWSLambda", "Lambda\nREST API", files, 150));
  els.push(...service("ddb2", 1010, 625, "AmazonDynamoDB", "DynamoDB", files, 150));
  els.push(arrow("users", "cf"), arrow("cf", "cog"), arrow("cog", "apigw2"), arrow("apigw2", "api"), arrow("api", "ddb2"));

  // clocks
  els.push(box("firms", 0, 885, 160, 132, "🛰️ NASA FIRMS\nfire history\n2022 to 2025", BG.orange, 18));
  els.push(...service("s3f", 200, 885, "AmazonSimpleStorageService", "S3\nfire layer", files, 180));
  els.push(...service("eb", 420, 885, "AmazonEventBridge", "EventBridge\nScheduler", files, 160));
  els.push(...service("jobs", 620, 885, "AWSLambda", "Lambda: risk,\noffers, reminders", files, 350));
  els.push(...service("ddb3", 1010, 885, "AmazonDynamoDB", "DynamoDB", files, 150));
  els.push(arrow("firms", "s3f"), arrow("eb", "jobs"), arrow("jobs", "ddb3"));

  // operations
  els.push(...service("ssm", 1250, 625, "AWSSystemsManager", "Parameter Store\nsecrets", files, 200));
  els.push(...service("cw", 1480, 625, "AmazonCloudWatch", "CloudWatch\nalarms", files, 190));
  els.push(...service("cfn", 1250, 885, "AWSCloudFormation", "SAM + GitHub\nActions (OIDC)", files, 200));
  els.push(...service("sns", 1480, 885, "AmazonSimpleNotificationService", "SNS\nemail alerts", files, 190));
  els.push(arrow("cw", "sns"));
  return { elements: els, files };
}

// ---------------------------------------------------------------- 5. burn-risk score
function risk() {
  REG = {};
  const els = [
    T(0, 0, "How the Burn Risk Radar scores a field, every hour", 34),
    box("u", 0, 110, 290, 130, "45% · urgency\ndays left to sow wheat", BG.yellow, 21),
    T(312, 150, "+", 40),
    box("b", 350, 110, 290, 130, "25% · no free baler\nbefore the deadline", BG.blue, 21),
    T(662, 150, "+", 40),
    box("h", 700, 110, 300, 130, "30% · fire history\nNASA FIRMS, 2022 to 2025", BG.orange, 21),
    T(1020, 150, "×", 40),
    box("k", 1060, 110, 260, 130, "1 if harvested\n0.35 if not yet", BG.gray, 21),
    box("s", 470, 330, 380, 110, "score 0 to 100", BG.white, 26),
    box("r", 120, 520, 290, 90, "🔴 60 and above: red", BG.red, 21),
    box("a", 515, 520, 290, 90, "🟠 40 to 59: amber", BG.orange, 21),
    box("g", 910, 520, 290, 90, "🟢 under 40: green", BG.green, 21),
  ];
  els.push(
    arrow("b", "s"), arrow("s", "r"), arrow("s", "a"), arrow("s", "g"),
    T(0, 650, "Booked or cleared fields score 0. A reported fire scores 100.\nAn officer can alert a whole red village on WhatsApp in one tap.", 20, MUTED),
  );
  return { elements: els, files: {} };
}

module.exports = [
  { name: "d1-the-3pm-gap", build: gap },
  { name: "d2-one-voice-note", build: flow },
  { name: "d3-offer-lifecycle", build: offer },
  { name: "d4-aws-architecture", build: architecture },
  { name: "d5-burn-risk-score", build: risk },
];
