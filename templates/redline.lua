-- redline.lua: turns the bill's change marks into real Word formatting.
--   {+ added text +}    -> underlined
--   [- deleted text -]  -> struck through
-- Marks may span several paragraphs, and may sit inside bold text.

local mode = nil  -- nil, "ins", or "del"

local function wrap(buf)
  if #buf == 0 then return nil end
  if mode == "ins" then return pandoc.Underline(buf) end
  if mode == "del" then return pandoc.Strikeout(buf) end
end

local process

-- Split a Str on the marker tokens so "+}." or "(B)" next to a marker still works.
local function split_str(text)
  local parts, i = {}, 1
  while i <= #text do
    local s, e = text:find("[%{%[][%+%-]", i)
    local s2, e2 = text:find("[%+%-][%}%]]", i)
    local ns, ne
    if s and (not s2 or s <= s2) then ns, ne = s, e else ns, ne = s2, e2 end
    if not ns then table.insert(parts, text:sub(i)); break end
    local tok = text:sub(ns, ne)
    local valid = tok == "{+" or tok == "+}" or tok == "[-" or tok == "-]"
    if not valid then
      table.insert(parts, text:sub(i, ne)); i = ne + 1
    else
      if ns > i then table.insert(parts, text:sub(i, ns - 1)) end
      table.insert(parts, {marker = tok}); i = ne + 1
    end
  end
  return parts
end

process = function(inlines)
  local out, buf = pandoc.List(), pandoc.List()
  local function flush()
    if mode then
      local w = wrap(buf); if w then out:insert(w) end
    else
      out:extend(buf)
    end
    buf = pandoc.List()
  end
  local skip_space = false
  for _, el in ipairs(inlines) do
    if el.t == "Str" then
      for _, part in ipairs(split_str(el.text)) do
        if type(part) == "table" then
          local m = part.marker
          if m == "{+" or m == "[-" then
            flush(); mode = (m == "{+") and "ins" or "del"; skip_space = true
          else
            -- drop the space that preceded a closing marker
            if #buf > 0 and buf[#buf].t == "Space" then buf:remove(#buf) end
            flush(); mode = nil
          end
        elseif part ~= "" then
          buf:insert(pandoc.Str(part)); skip_space = false
        end
      end
    elseif el.t == "Space" and skip_space then
      skip_space = false
    elseif el.content and (el.t == "Strong" or el.t == "Emph" or el.t == "Span") then
      local saved = mode
      flush()
      el.content = process(el.content)
      buf:insert(el)
      flush()
      skip_space = false
      if saved ~= mode then -- a marker opened or closed inside the bold text
      end
    else
      buf:insert(el); skip_space = false
    end
  end
  flush()
  return out
end

-- Underline/strike must be reapplied at the start of each paragraph that continues a mark.
function Para(el) el.content = process(el.content); return el end
function Plain(el) el.content = process(el.content); return el end
