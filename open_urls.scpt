on is_url_open(url)
    tell application "Google Chrome"
        set window_list to every window
        repeat with the_window in window_list
            set tab_list to every tab of the_window
            repeat with the_tab in tab_list
                if URL of the_tab is url then
                    return true
                end if
            end repeat
        end repeat
    end tell
    return false
end is_url_open

set urls to {"http://localhost:8501", "http://localhost:8000/docs", "http://localhost:5555", "http://localhost:4444", "http://localhost:8081"}
tell application "Google Chrome"
    repeat with the_url in urls
        do shell script "echo \" Opening URL: " & the_url & "\""
        if not is_url_open(the_url) then
            open location the_url
        else
            do shell script "echo " & the_url & " is already open"
        end if
    end repeat
end tell

curl -s "http://localhost:9222/json" | grep -oP '(?<="url":")[^"]+'