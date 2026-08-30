local iterations = os.getenv("CPU_ITERATIONS") or "2000"

function request()
    return wrk.format("GET", "/compute?iterations=" .. iterations .. "&data=benchmark-payload")
end