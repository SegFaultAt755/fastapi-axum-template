local user_count = tonumber(os.getenv("USER_COUNT")) or 100000
local iterations = os.getenv("CPU_ITERATIONS") or "2000"

function init(args)
    math.randomseed(os.time())
end

function request()
    local user_id = math.random(1, user_count)
    return wrk.format("GET", "/compute-db/" .. user_id .. "?iterations=" .. iterations)
end