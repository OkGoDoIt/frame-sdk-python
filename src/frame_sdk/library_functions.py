from .bluetooth import FrameDataTypePrefixes

# these are some helper functions that we run on the Frame.  The SDK will not work well if these do not exist.  Every time you connect to a Frame, the SDK will automatically inject these functions into the Frame.
library_print_long = """
function prntLng(stringToPrint)
    local mtu = frame.bluetooth.max_length()
    local len = string.len(stringToPrint)
    if len <= mtu - 3 then
        print(stringToPrint)
        return
    end
    local i = 1
    local chunkIndex = 0
    while i <= len do
        local j = i + mtu - 4
        if j > len then
            j = len
        end
        local chunk = string.sub(stringToPrint, i, j)
        print('\\x"""+FrameDataTypePrefixes.LONG_TEXT.value_as_hex+"""'..chunk)
        chunkIndex = chunkIndex + 1
        i = j + 1
    end
    print('\\x"""+FrameDataTypePrefixes.LONG_TEXT_END.value_as_hex+"""'..chunkIndex)
end
function sendPartial(dataToSend, max_size)
    local len = string.len(dataToSend)
    local i = 1
    local chunkIndex = 0
    while i <= len do
        local j = i + max_size - 4
        if j > len then
            j = len
        end
        local chunk = string.sub(dataToSend, i, j)
        while true do
            if pcall(frame.bluetooth.send, '\\x"""+FrameDataTypePrefixes.LONG_DATA.value_as_hex+"""' .. chunk) then
                break
            end
        end
        chunkIndex = chunkIndex + 1
        i = j + 1
    end
    return chunkIndex
end
function printCompleteFile(filename)
    local mtu = frame.bluetooth.max_length()
    local f = frame.file.open(filename, "read")
    local chunkIndex = 0
    local chunk = ""
    while true do
        local new_chunk = f:read()
        if new_chunk == nil then
            if string.len(chunk) > 0 then
                chunkIndex = chunkIndex + sendPartial(chunk, mtu)
                break
            end
            break
        end
        if string.len(new_chunk) == 512 then
            chunk = chunk .. new_chunk
        else
            chunk = chunk .. new_chunk .. "\\n"
        end

        while string.len(chunk) > mtu - 4 do
            local chunk_to_send = string.sub(chunk, 1, mtu - 4)
            chunkIndex = chunkIndex + 1
            chunk = string.sub(chunk, mtu - 3)
            while true do
                if pcall(frame.bluetooth.send, '\\x"""+FrameDataTypePrefixes.LONG_DATA.value_as_hex+"""' .. chunk_to_send) then
                    break
                end
            end
        end
    end
    while true do
        if pcall(frame.bluetooth.send, '\\x"""+FrameDataTypePrefixes.LONG_DATA_END.value_as_hex+"""' .. chunkIndex) then
            break
        end
    end
    f:close()
end
function cameraCaptureAndSend(quality,autoExpTimeDelay,autofocusType,resolution,pan)
    local last_autoexp_time = 0
    local state = 'EXPOSING'
    local state_time = frame.time.utc()
    local chunkIndex = 0
    if autoExpTimeDelay == nil then
        state = 'CAPTURE'
    end

    while true do
        if state == 'EXPOSING' then
            if frame.time.utc() - last_autoexp_time > 0.1 then
                frame.camera.auto { metering = autofocusType }
                last_autoexp_time = frame.time.utc()
            end
            if frame.time.utc() > state_time + autoExpTimeDelay then
                state = 'CAPTURE'
            end
        elseif state == 'CAPTURE' then
            frame.camera.capture { resolution = resolution, quality = quality, pan = pan }
            state_time = frame.time.utc()
            state = 'WAIT'
        elseif state == 'WAIT' then
            if frame.camera.image_ready() then
                state = 'SEND'
            end
        elseif state == 'SEND' then
            local i = frame.camera.read(frame.bluetooth.max_length() - 1)
            if (i == nil) then
                state = 'DONE'
            else
                while true do
                    if pcall(frame.bluetooth.send, '\\x"""+FrameDataTypePrefixes.LONG_DATA.value_as_hex+"""' .. i) then
                        break
                    end
                end
                chunkIndex = chunkIndex + 1
            end
        elseif state == 'DONE' then
            while true do
                if pcall(frame.bluetooth.send, '\\x"""+FrameDataTypePrefixes.LONG_DATA_END.value_as_hex+"""' .. chunkIndex) then
                    break
                end
            end
            break
        end
    end
end
function drawRect(x,y,width,height,color)
    frame.display.bitmap(x,y,width,2,color,string.rep("\\xFF",math.floor(width/8*height)))
end

function scrollText(text, line_height, total_height, lines_per_frame, delay, text_color_name, letter_spacing)
    local lines = {}
    local line_count = 1
    local start = 1
    while true do
        local found_start, found_end = string.find(text, "\\n", start)
        if not found_start then
            table.insert(lines, string.sub(text, start))
            break
        end
        table.insert(lines, string.sub(text, start, found_start - 1))
        line_count = line_count + 1
        start = found_end + 1
    end
    local i = 0
    while i < total_height - (400 - line_height * 2) do
        local start_time = frame.time.utc()
        if i == 0 then
            start_time = start_time + (2 * line_height / lines_per_frame * delay)
        end
        local first_line_index = math.floor(i / line_height) + 1
        local first_line_offset = i % line_height
        local y = line_height - first_line_offset
        for j = first_line_index, line_count do
            local line = lines[j]
            frame.display.text(line, 1, y, {color=text_color_name, spacing=letter_spacing})
            y = y + line_height
            if y > 400 - line_height then
                break
            end
        end
        drawRect(1, 1, 640, line_height, 15)
        drawRect(1, 400 - line_height, 640, line_height, 15)
        frame.display.show()
        while frame.time.utc() - start_time < delay do
        end
        i = i + lines_per_frame
    end
    local extra_time = frame.time.utc() + (1 * line_height / lines_per_frame * delay)
    while frame.time.utc() < extra_time do
    end
end

function microphoneRecordAndSend(sample_rate, bit_depth, max_time_in_seconds)
    frame.microphone.start{sample_rate=sample_rate, bit_depth=bit_depth}
    local end_time = frame.time.utc() + 60 * 60 * 24
    local max_packet_size = frame.bluetooth.max_length() - 4
    if max_time_in_seconds ~= nil then
        end_time = frame.time.utc() + max_time_in_seconds
    end
    local chunk_count = 0

    if max_packet_size % 2 ~= 0 then
        max_packet_size = max_packet_size - 1
    end

    while frame.time.utc() < end_time do
        s = frame.microphone.read(max_packet_size)
        if s == nil then
            break
        end
        if s ~= '' then
            while true do
                if max_time_in_seconds ~= nil then
                    if pcall(frame.bluetooth.send, '\\x"""+FrameDataTypePrefixes.LONG_DATA.value_as_hex+"""' .. s) then
                        break
                    end
                else
                    if pcall(frame.bluetooth.send, '\\x"""+FrameDataTypePrefixes.MIC_DATA.value_as_hex+"""' .. s) then
                        break
                    end
                end
            end
            chunk_count = chunk_count + 1
        end
    end
    if max_time_in_seconds ~= nil then
        frame.bluetooth.send('\\x"""+FrameDataTypePrefixes.LONG_DATA_END.value_as_hex+"""' .. tostring(chunk_count))
    end
    frame.microphone.stop()
end
"""