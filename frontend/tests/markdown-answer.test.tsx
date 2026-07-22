import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MarkdownAnswer } from "../components/MarkdownAnswer";
describe("MarkdownAnswer",()=>{it("renders Markdown and only activates known citations",()=>{const click=vi.fn();render(<MarkdownAnswer content={"**Important** [S1] [S9]"} sources={[{citation_id:"S1",page:2,chunk_id:"a",similarity:.7,content:"passage"}]} onCitation={click}/>);expect(screen.getByText("Important").tagName).toBe("STRONG");fireEvent.click(screen.getByRole("button",{name:"Open source S1"}));expect(click).toHaveBeenCalledTimes(1);expect(screen.queryByRole("button",{name:"Open source S9"})).toBeNull()})})
