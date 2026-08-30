local user_count = tonumber(os.getenv("USER_COUNT")) or 100000

function init(args)
    math.randomseed(os.time())
end

function request()
    local user_id = math.random(1, user_count)
    return wrk.format("GET", "/user/" .. user_id)
end