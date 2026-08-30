local user_count = tonumber(os.getenv("USER_COUNT")) or 100000

function init(args)
    math.randomseed(os.time())
end

function request()
    local user_id = math.random(1, user_count)
    local age = math.random(18, 80)
    return wrk.format("PUT", "/user/" .. user_id .. "/age/" .. age)
end