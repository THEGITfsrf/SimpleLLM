import time
import multiprocessing

def burn():
    while True:
        pass  # max CPU loop

if __name__ == "__main__":
    procs = []

    for _ in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=burn)
        p.start()
        procs.append(p)

    time.sleep(10)  # run for 10 seconds

    for p in procs:
        p.terminate()