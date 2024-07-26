

def timeformat(time, dayname, hourname, minutename):
    return str(time.days) + dayname + " " + str(time.seconds // 3600) + hourname + " " + str(time.seconds%3600//60) + minutename

