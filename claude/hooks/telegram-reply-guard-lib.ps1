# telegram-reply-guard-lib.ps1
# Core decision logic for telegram-reply-guard.ps1, extracted so it can be
# dot-sourced from both the hook and its tests.
#
# Performance: transcripts can be several MB / tens of thousands of lines.
# We stream with [System.IO.File]::ReadLines (no full-file array-in-memory)
# and pre-filter each line as a plain string BEFORE attempting a JSON
# parse. Only lines containing one of the two marker substrings we care
# about are ever parsed, so cost stays proportional to the (small) number
# of Telegram-related lines, not total transcript size.
#
# Role-bug resilience: a known Claude Code bug can record an incoming
# Telegram message with type="assistant" instead of "user". We therefore
# do NOT gate incoming-candidate detection on type/role at all -- only on
# the <channel source="plugin:telegram:telegram" ...> marker text. A line
# that also contains the reply marker is treated as a reply candidate
# ONLY (excluded from incoming candidates), so the reply tool_use call
# itself is never mistaken for a new incoming message.
#
# Quoted-tag resilience: the channel marker can also appear QUOTED inside
# tool activity -- e.g. a Write/Agent tool_use whose input contains the
# tag (design docs, test fixtures) or a tool_result from Reading a file
# that contains it. Those are artifacts, not real incoming messages, and
# would cause false blocks after a reply was already sent. Real incoming
# messages (including role-bug ones) are recorded as plain text entries
# with no tool blocks, so any line containing "tool_use" or "tool_result"
# is excluded from incoming candidates at the pre-filter stage.

function Get-ReplyGuardDecision {
    # Returns 'block' or 'allow'.
    param([string]$TranscriptPath)

    # NOTE: matched against the RAW (still JSON-encoded) line. For real
    # incoming messages the tag lives inside a JSON string value, so its
    # quotes are backslash-escaped: <channel source=\"plugin:telegram:telegram\"
    # We match that escaped form (plus the unescaped form defensively).
    # The FULL tag is required on purpose: the bare server id
    # "plugin:telegram:telegram" also appears in transcript METADATA
    # (e.g. attributionMcpServer on assistant entries produced around a
    # reply call), which is not an incoming message and must not count.
    $channelMarkerEscaped = '<channel source=\"plugin:telegram:telegram\"'
    $channelMarkerPlain = '<channel source="plugin:telegram:telegram"'
    $replyMarker = 'mcp__plugin_telegram_telegram__reply'

    $lastTelegram = [datetime]::MinValue
    $lastReply = [datetime]::MinValue
    $foundTelegram = $false

    foreach ($line in [System.IO.File]::ReadLines($TranscriptPath)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }

        $hasReply = $line.Contains($replyMarker)
        $hasChannel = $line.Contains($channelMarkerEscaped) -or $line.Contains($channelMarkerPlain)
        if (-not $hasReply -and -not $hasChannel) { continue }

        try { $e = $line | ConvertFrom-Json } catch { continue }
        if (-not $e.timestamp) { continue }
        try { $ts = [datetime]$e.timestamp } catch { continue }

        if ($hasReply) {
            # Strict match, same as legacy logic: only a real tool_use
            # block for the reply tool counts.
            $content = $e.message.content
            if ($content -and -not ($content -is [string])) {
                foreach ($b in $content) {
                    if ($b.type -eq 'tool_use' -and $b.name -eq 'mcp__plugin_telegram_telegram__reply') {
                        if ($ts -gt $lastReply) { $lastReply = $ts }
                    }
                }
            }
        }
        elseif ($hasChannel) {
            # Quoted-tag exclusion: tool_use/tool_result lines quote the
            # tag as an artifact (Write input, Read result, agent prompt),
            # they are never a real incoming message.
            if ($line.Contains('"tool_use"') -or $line.Contains('"tool_result"')) { continue }
            $foundTelegram = $true
            if ($ts -gt $lastTelegram) { $lastTelegram = $ts }
        }
    }

    if ($foundTelegram -and $lastTelegram -gt $lastReply) { return 'block' }
    return 'allow'
}
