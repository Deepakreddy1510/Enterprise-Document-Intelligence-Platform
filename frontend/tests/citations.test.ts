import { describe, expect, it } from "vitest";
import { linkifyCitations } from "../components/MarkdownAnswer";

describe("linkifyCitations", () => {
  it("does not replace unknown markers and preserves surrounding Markdown", () => {
    const markdown = "- **Evidence** [S1]\n\n| A | B |\n| - | - |\n| [S2] | text |";
    expect(linkifyCitations(markdown, [{ citation_id: "S1", page: 1, chunk_id: "chunk", similarity: 0.8, content: "source" }])).toBe("- **Evidence** [S1](citation:S1)\n\n| A | B |\n| - | - |\n| [S2] | text |");
  });
});
