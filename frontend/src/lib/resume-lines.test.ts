import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  applyWordListEnter,
  fromBulletEditorValue,
  parseParagraphs,
  toBulletEditorValue,
} from "./resume-lines";

describe("Word-like resume list enter", () => {
  it("turns Enter on a filled bullet into a new bullet", () => {
    const value = "• Track food";
    const next = applyWordListEnter(value, value.length, value.length);
    assert.equal(next.value, "• Track food\n• ");
    assert.equal(next.cursor, next.value.length);
  });

  it("turns Enter on an empty bullet into a plain line break", () => {
    const value = "• Track food\n• ";
    const next = applyWordListEnter(value, value.length, value.length);
    assert.equal(next.value, "• Track food\n");
    assert.deepEqual(fromBulletEditorValue(next.value), ["Track food"]);
  });
});

describe("resume description parsing", () => {
  it("keeps a paragraph as one block", () => {
    assert.deepEqual(
      parseParagraphs("Track food items. Remind the household."),
      ["Track food items. Remind the household."],
    );
  });

  it("round-trips bullets without inventing extra items", () => {
    const lines = ["Track food items", "Remind the household"];
    assert.deepEqual(
      fromBulletEditorValue(toBulletEditorValue(lines)),
      lines,
    );
  });
});
