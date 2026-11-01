-- no-rules.lua: drops Markdown "---" dividers, which Word renders as heavy decorative lines.
-- Headings already separate the sections of a memo.
function HorizontalRule() return {} end
