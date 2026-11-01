-- footnotes.lua: converts hand-typed superscript citations into real Word footnotes.
-- The Markdown keeps its "¹ R.C. 3109.042(A). ² ..." citation block (between <small> tags);
-- this filter moves each citation into a footnote at the matching superscript and removes the block.

local SUP = { ["⁰"]="0", ["¹"]="1", ["²"]="2", ["³"]="3", ["⁴"]="4",
              ["⁵"]="5", ["⁶"]="6", ["⁷"]="7", ["⁸"]="8", ["⁹"]="9" }

-- Split a string into a list of {text=...} and {num=...} pieces.
local function split(text)
  local parts, buf, digits = {}, "", ""
  for _, cp in utf8.codes(text) do
    local ch = utf8.char(cp)
    if SUP[ch] then
      if buf ~= "" then table.insert(parts, {text = buf}); buf = "" end
      digits = digits .. SUP[ch]
    else
      if digits ~= "" then table.insert(parts, {num = tonumber(digits)}); digits = "" end
      buf = buf .. ch
    end
  end
  if digits ~= "" then table.insert(parts, {num = tonumber(digits)}) end
  if buf ~= "" then table.insert(parts, {text = buf}) end
  return parts
end

local function has_sup(text)
  for _, cp in utf8.codes(text) do if SUP[utf8.char(cp)] then return true end end
  return false
end

function Pandoc(doc)
  local notes, keep, in_block = {}, pandoc.List(), false
  -- 1. Collect citations from the <small> block.
  -- The <small> tags arrive either as raw blocks or as one-element paragraphs.
  local function tag(b)
    if b.t == "RawBlock" then return b.text end
    if (b.t == "Para" or b.t == "Plain") and #b.content == 1 and b.content[1].t == "RawInline" then
      return b.content[1].text
    end
  end
  for _, b in ipairs(doc.blocks) do
    local t = tag(b)
    if t and t:match("^<small>") then in_block = true
    elseif t and t:match("^</small>") then in_block = false
    elseif in_block and (b.t == "Para" or b.t == "Plain") then
      local cur = nil
      for _, el in ipairs(b.content) do
        if el.t == "Str" and has_sup(el.text) then
          for _, p in ipairs(split(el.text)) do
            if p.num then cur = p.num; notes[cur] = pandoc.List()
            elseif cur then notes[cur]:insert(pandoc.Str(p.text)) end
          end
        elseif cur then
          notes[cur]:insert(el)
        end
      end
    else
      keep:insert(b)
    end
  end
  if next(notes) == nil then return doc end
  for _, n in pairs(notes) do
    while #n > 0 and (n[1].t == "Space" or n[1].t == "SoftBreak") do n:remove(1) end
    while #n > 0 and (n[#n].t == "Space" or n[#n].t == "SoftBreak") do n:remove(#n) end
  end
  -- 2. Replace superscripts in the body with footnotes.
  return pandoc.Pandoc(keep, doc.meta):walk({
    Str = function(el)
      if not has_sup(el.text) then return nil end
      local out = pandoc.List()
      for _, p in ipairs(split(el.text)) do
        if p.num and notes[p.num] then
          out:insert(pandoc.Note({pandoc.Para(notes[p.num])}))
        elseif p.text then out:insert(pandoc.Str(p.text)) end
      end
      return out
    end
  })
end
