import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { nextTypedText } from "./guide-typewriter";

function typedFrames(target: string): string[] {
  const frames: string[] = [];
  let shown = "";
  let guard = 0;
  while (shown !== target) {
    shown = nextTypedText(shown, target);
    frames.push(shown);
    guard += 1;
    if (guard > target.length + 8) break;
  }
  return frames;
}

describe("public guide typewriter", () => {
  it("reveals a canned Chinese reply in more than one frame", () => {
    const target = "可以问我代表项目。";
    const frames = typedFrames(target);

    assert.ok(frames.length > 1, "visitor replies must not appear in one paint");
    assert.notEqual(frames[0], target);
    assert.equal(frames.at(-1), target);
  });

  it("advances one CJK character at a time", () => {
    assert.equal(nextTypedText("", "你好"), "你");
    assert.equal(nextTypedText("你", "你好"), "你好");
  });

  it("restarts when the live reply is replaced", () => {
    assert.equal(nextTypedText("旧回复全文", "你好"), "你");
  });
});
