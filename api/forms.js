const allowedKinds = new Set(["contact", "crew-application"]);

function text(value, limit = 5000) {
  return typeof value === "string" ? value.trim().slice(0, limit) : "";
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, message: "Method not allowed" });
  }

  const body = req.body && typeof req.body === "object" ? req.body : {};
  if (text(body.companyWebsite, 500)) {
    return res.status(202).json({ ok: true });
  }

  const kind = text(body.kind, 40);
  const firstName = text(body.firstName, 100);
  const lastName = text(body.lastName, 100);
  const email = text(body.email, 254);
  const message = text(body.message, 5000);
  const phone = text(body.phone, 80);
  const position = text(body.position, 120);
  const experience = text(body.experience, 20);
  const notes = text(body.notes, 3000);

  if (!allowedKinds.has(kind) || !firstName || !lastName || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ ok: false, message: "Please check the required fields." });
  }
  if (kind === "contact" && !message) {
    return res.status(400).json({ ok: false, message: "Please add a message." });
  }
  if (kind === "crew-application" && (!phone || !position)) {
    return res.status(400).json({ ok: false, message: "Please add your phone number and position of interest." });
  }

  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.FLEET_FORMS_FROM;
  if (!apiKey || !from) {
    return res.status(503).json({ ok: false, code: "NOT_CONFIGURED", message: "Online form delivery has not been configured." });
  }

  const isCrew = kind === "crew-application";
  const lines = isCrew
    ? [`Name: ${firstName} ${lastName}`, `Email: ${email}`, `Phone: ${phone}`, `Position: ${position}`, `Years experience: ${experience || "Not provided"}`, `Notes: ${notes || "Not provided"}`]
    : [`Name: ${firstName} ${lastName}`, `Email: ${email}`, "", message];
  const subject = isCrew ? `Vessel crew application — ${firstName} ${lastName}` : `Website inquiry — ${firstName} ${lastName}`;

  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from,
        to: process.env.FLEET_FORMS_TO || "sales@fleetfisheries.com",
        reply_to: email,
        subject,
        text: lines.join("\n"),
      }),
    });
    if (!response.ok) {
      return res.status(502).json({ ok: false, message: "The message service could not accept this submission." });
    }
    return res.status(200).json({ ok: true });
  } catch {
    return res.status(502).json({ ok: false, message: "The message service is temporarily unavailable." });
  }
};
