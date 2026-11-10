/**
 * nidhogg.ts — the project harness as a native pi extension.
 *
 * Why this exists: the harness started life as a pile of standalone python scripts that the agent had
 * to remember to run (`tools/doctor.py`, `tools/claim.py`, `game.py`, ...). Remembering is exactly what
 * fails after a compaction, and Pro's review said it plainly: "doctor.py is attest.py again - a nice
 * report nothing consumes". So the same capabilities are now registered as pi TOOLS, which the model
 * sees in its tool list, plus a `/nid` command and a `tool_call` guard that refuses the one class of
 * action that kept corrupting this project: writing the game's input files while someone else owns the
 * game.
 *
 * Tools registered:
 *   nid_status   environment + plan + slot in one call (was tools/doctor.py + plan + gameslot)
 *   nid_game     drive the game: status | enter | state | do | rounds | shot   (was game.py)
 *   nid_plan     show | next | start | done (needs evidence) | block | add    (was tools/plan.py)
 *   nid_claim    record (needs --cmd and --falsifier) | verify | fixtures     (was tools/claim.py)
 *   nid_slot     acquire | release | status                                  (was tools/gameslot.py)
 *   nid_mail     post | check | inbox                                        (was tools/mailbox.py)
 *   nid_agents   list | spawn | tail | wait | stop                           (was tools/agents.py)
 *
 * The command `/nid` prints the same status block.
 *
 * Everything delegates to the existing python modules rather than reimplementing them: the python is
 * tested, and duplicating the room table or the band-matching navigation in TypeScript would create two
 * sources of truth - the exact failure mode this project keeps hitting.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";

const run = promisify(execFile);

const PYTHON =
  process.env.NID_PYTHON ||
  path.join(process.env.HOME || "", "Projects/nidhogg-rl/.venv/bin/python");

function repo(): string {
  return process.cwd();
}

async function py(script: string, args: string[] = [], timeout = 120_000) {
  const file = path.join(repo(), script);
  if (!fs.existsSync(file)) {
    throw new Error(`missing ${script} (is the cwd the nidhogg-pau repo?)`);
  }
  try {
    const { stdout, stderr } = await run(PYTHON, [file, ...args], {
      cwd: repo(),
      timeout,
      maxBuffer: 8 * 1024 * 1024,
    });
    return (stdout || "") + (stderr || "");
  } catch (e: any) {
    const out = `${e.stdout || ""}${e.stderr || ""}`;
    throw new Error(out.trim() || e.message);
  }
}

/** One compact status line: process/fps/room, plan step, and who owns the game. */
async function statusText(): Promise<string> {
  const parts: string[] = [];
  try {
    const doc = await py("tools/doctor.py", ["--json"]);
    const d = JSON.parse(doc);
    const get = (name: string) =>
      (d.checks || []).find((c: any) => c.check.startsWith(name))?.detail ?? "?";
    parts.push(`env ${d.overall}: fps ${get("frame rate")}, room ${get("room")}, ${get("game processes")}`);
  } catch (e: any) {
    parts.push(`env ERROR: ${String(e.message).slice(0, 120)}`);
  }
  try {
    const nxt = JSON.parse(await py("tools/plan.py", ["next"]));
    parts.push(`plan ${nxt.id}: ${nxt.title}`);
  } catch {
    parts.push("plan: none open");
  }
  try {
    parts.push(`slot: ${(await py("tools/gameslot.py", ["status"])).trim()}`);
  } catch {
    parts.push("slot: ?");
  }
  return parts.join("\n");
}

export default function (pi: ExtensionAPI) {
  // ---------------------------------------------------------------- nid_status
  pi.registerTool({
    name: "nid_status",
    label: "Nidhogg status",
    description:
      "One call that tells you whether the training environment is sane: game processes, frame rate, " +
      "priority, room, file freshness, who owns the game slot, and the current plan step. Run this " +
      "before any other nidhogg tool, and again whenever something looks wrong.",
    parameters: Type.Object({}),
    async execute() {
      const text = await statusText();
      return { content: [{ type: "text" as const, text }], details: undefined };
    },
  });

  // ---------------------------------------------------------------- nid_game
  pi.registerTool({
    name: "nid_game",
    label: "Drive the game",
    description:
      "Single choke point for the real game. action=status|enter|state|do|rounds|shot. " +
      "'do' takes act (left|right|attack|jump|crouch|enter|esc) and optional frames (game frames, not " +
      "seconds). Movement keys are refused outside an arena room because in menus they change the " +
      "game's settings. 'rounds' watches for round transitions, the measurement the project is missing.",
    parameters: Type.Object({
      action: Type.String({ description: "status | enter | state | do | rounds | shot" }),
      act: Type.Optional(Type.String({ description: "for action=do: left right attack jump crouch enter esc" })),
      frames: Type.Optional(Type.Number({ description: "for action=do: how many game frames to hold" })),
      seconds: Type.Optional(Type.Number({ description: "for action=rounds: how long to watch" })),
    }),
    async execute(_id, params: any) {
      const a = String(params.action || "status");
      const args: string[] = [a];
      if (a === "do") {
        if (!params.act) throw new Error("action=do needs act");
        args.push(String(params.act));
        if (params.frames) args.push(String(Math.round(params.frames)));
      }
      if (a === "rounds") args.push(String(params.seconds ?? 60));
      const text = await py("game.py", args, 300_000);
      return { content: [{ type: "text" as const, text: text.trim() || "(no output)" }], details: undefined };
    },
  });

  // ---------------------------------------------------------------- nid_plan
  pi.registerTool({
    name: "nid_plan",
    label: "Work the plan",
    description:
      "The project plan. action=show|next|start|done|block|add. A step can only be closed with " +
      "evidence: 'done' requires evidence (an existing file path, or a command that runs and produces " +
      "output). Use 'next' to find the single step to work on.",
    parameters: Type.Object({
      action: Type.String({ description: "show | next | start | done | block | add" }),
      id: Type.Optional(Type.String({ description: "step id" })),
      evidence: Type.Optional(Type.String({ description: "for done: file path or command that proves it" })),
      reason: Type.Optional(Type.String({ description: "for block: why" })),
      title: Type.Optional(Type.String({ description: "for add: the step title" })),
      accept: Type.Optional(Type.String({ description: "for add: acceptance criterion" })),
    }),
    async execute(_id, params: any) {
      const a = String(params.action || "next");
      const args: string[] = [a];
      if (a === "add") {
        if (!params.title) throw new Error("action=add needs title");
        args.push(String(params.title));
        if (params.accept) args.push("--accept", String(params.accept));
      } else if (params.id) {
        args.push(String(params.id));
      }
      if (params.evidence) args.push("--evidence", String(params.evidence));
      if (params.reason) args.push("--reason", String(params.reason));
      const text = await py("tools/plan.py", args, 300_000);
      return { content: [{ type: "text" as const, text: text.trim() }], details: undefined };
    },
  });

  // ---------------------------------------------------------------- nid_claim
  pi.registerTool({
    name: "nid_claim",
    label: "Claims ledger",
    description:
      "Record or verify measurements. A claim REQUIRES cmd (the command that produces the evidence) and " +
      "falsifier (a command that must exit 0 if the claim is FALSE). Without a falsifier a wrong-but-" +
      "stable number verifies forever. action=record|verify|fixtures.",
    parameters: Type.Object({
      action: Type.String({ description: "record | verify | fixtures" }),
      text: Type.Optional(Type.String({ description: "for record: what is asserted" })),
      cmd: Type.Optional(Type.String({ description: "for record: command producing the evidence" })),
      falsifier: Type.Optional(Type.String({ description: "for record: command that succeeds if the claim is false" })),
    }),
    async execute(_id, params: any) {
      const a = String(params.action || "verify");
      if (a === "record") {
        if (!params.text || !params.cmd) throw new Error("record needs text and cmd");
        const args = ["record", String(params.text), "--cmd", String(params.cmd)];
        if (params.falsifier) args.push("--falsifier", String(params.falsifier));
        return {
          content: [{ type: "text" as const, text: (await py("tools/claim.py", args)).trim() }],
          details: undefined,
        };
      }
      const text = await py("tools/claim.py", [a], 300_000);
      return { content: [{ type: "text" as const, text: text.trim() }], details: undefined };
    },
  });

  // ---------------------------------------------------------------- nid_slot
  pi.registerTool({
    name: "nid_slot",
    label: "Game slot",
    description:
      "There is exactly ONE game. Anything that launches it, presses its keys or kills it must hold the " +
      "slot. action=acquire|release|status. acquire takes purpose.",
    parameters: Type.Object({
      action: Type.String({ description: "acquire | release | status" }),
      purpose: Type.Optional(Type.String({ description: "for acquire: what you are about to do" })),
      ttl: Type.Optional(Type.Number({ description: "for acquire: lease seconds (default 7200)" })),
    }),
    async execute(_id, params: any) {
      const a = String(params.action || "status");
      const args: string[] = [a];
      if (a === "acquire") {
        args.push(String(params.purpose || "unspecified"), "--ttl", String(Math.round(params.ttl ?? 7200)));
      }
      const text = await py("tools/gameslot.py", args);
      return { content: [{ type: "text" as const, text: text.trim() }], details: undefined };
    },
  });

  // ---------------------------------------------------------------- nid_mail
  pi.registerTool({
    name: "nid_mail",
    label: "Mailbox",
    description:
      "Two-way messages with the engineer session. action=check (unread for you) | post (to engineer) | " +
      "inbox (everything addressed to operator).",
    parameters: Type.Object({
      action: Type.String({ description: "check | post | inbox" }),
      text: Type.Optional(Type.String({ description: "for post" })),
    }),
    async execute(_id, params: any) {
      const a = String(params.action || "check");
      const args: string[] = [a];
      if (a === "post") {
        if (!params.text) throw new Error("post needs text");
        args.push("--to", "engineer", "--from", "operator", String(params.text));
      } else {
        args.push("--as", "operator");
      }
      const text = await py("tools/mailbox.py", args);
      return { content: [{ type: "text" as const, text: text.trim() }], details: undefined };
    },
  });

  // ---------------------------------------------------------------- nid_agents
  pi.registerTool({
    name: "nid_agents",
    label: "Subagents",
    description:
      "Manage subagent sessions. action=list|spawn|tail|wait|stop. 'spawn' needs name, task_file and " +
      "optionally persona (.pi/agents/goldfish.md or decomp.md) and game=true to lease the game slot " +
      "for the child. Children write their deliverable to a results file.",
    parameters: Type.Object({
      action: Type.String({ description: "list | spawn | tail | wait | stop" }),
      name: Type.Optional(Type.String()),
      task_file: Type.Optional(Type.String({ description: "for spawn: path to a task description" })),
      persona: Type.Optional(Type.String({ description: "for spawn: project persona file" })),
      game: Type.Optional(Type.Boolean({ description: "for spawn: lease the game slot to the child" })),
      seconds: Type.Optional(Type.Number({ description: "for wait" })),
    }),
    async execute(_id, params: any) {
      const a = String(params.action || "list");
      const args: string[] = [a];
      if (a === "spawn") {
        if (!params.name || !params.task_file) throw new Error("spawn needs name and task_file");
        args.push(String(params.name), String(params.task_file));
        if (params.persona) args.push("--persona", String(params.persona));
        if (params.game) args.push("--game");
      } else if (a !== "list") {
        if (!params.name) throw new Error(`${a} needs name`);
        args.push(String(params.name));
        if (a === "wait" && params.seconds) args.push(String(Math.round(params.seconds)));
      }
      const text = await py("tools/agents.py", args, 400_000);
      return { content: [{ type: "text" as const, text: text.trim() }], details: undefined };
    },
  });

  // ---------------------------------------------------------------- /nid
  pi.registerCommand("nid", {
    description: "Nidhogg harness status: environment, plan step, game slot",
    handler: async (_args, ctx) => {
      const text = await statusText();
      ctx.ui.notify(text, "info");
    },
  });

  // ---------------------------------------------------------------- guard
  /**
   * THE GUARD. Pro's verdict was that advisory files are decoration: a rogue subagent wrote
   * /tmp/nid_keys_0.txt directly and nothing would have stopped it. This refuses any bash command that
   * writes the game's control files unless the writer holds the slot.
   *
   * It is deliberately narrow: it only inspects commands that mention the game's control paths, so it
   * cannot get in the way of ordinary work.
   */
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return;
    const cmd = String((event.input as any)?.command || "");
    if (!/nid_(keys|click|roomgoto|speed|scan|objs|vars|localtest|startmatch)/.test(cmd)) return;

    let holder = "";
    try {
      holder = (await py("tools/gameslot.py", ["status"])).trim();
    } catch {
      return;
    }
    if (holder.startsWith("FREE")) return;

    // A blocking confirm() is FATAL for an autonomous agent: the operator session sat on a Yes/No
    // prompt and stopped working. Decide from the slot contents instead, and fail closed with a
    // reason the agent can act on.
    const role = process.env.NID_ROLE || "operator";
    if (holder.toLowerCase().includes(role.toLowerCase())) return;   // it is our own lease

    return {
      block: true,
      reason:
        `game slot is held by another owner (${holder}). ` +
        `If that holder is dead, run 'python3 tools/gameslot.py force' or 'acquire' to take over; ` +
        `otherwise wait for it to release. Do not write the game's control files while it holds the slot.`,
    };
  });
}
