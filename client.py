import socket, logging, yaml
from logging.handlers import RotatingFileHandler

LOG: object = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

file_handler: object = RotatingFileHandler("log/client.log", maxBytes=5*1024*1024, backupCount=5)
stream_handler: object = logging.StreamHandler()

formatter: object = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

LOG.addHandler(file_handler)
LOG.addHandler(stream_handler)

CONFIG_LS: list = [
    "settings"
] # will be used when fetch_config is called and will load all yaml config listed

def fetch_config() -> dict:
    ls: list = {}
    try: 
        for f in CONFIG_LS:
            LOG.debug(f"---> Config name: {f}")
            with open("config/"+f+".yaml", "r") as conf:
                ls[f] = yaml.safe_load(conf)
    except:
        LOG.error("*** Something went wrong loading configs ***")
        sys.exit()
    LOG.info("---> Succesful loading of config")
    return ls

if __name__ == '__main__':
    LOG.info("==== Setting Up the Connection ====")
    conf: dict = fetch_config()
    host: str = conf["settings"]["ip"]
    port: int = int(conf["settings"]["port"])

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect((host, port))

    while True:
        input_string = input("Enter a string to send to the server (or 'exit' to quit): ")
        
        if input_string.lower() == 'exit':
            print("Exiting...")
            break

        client_sock.send(input_string.encode('utf-8'))
        print(f"Sent to server: {input_string}")

        response = client_sock.recv(1024).decode('utf-8')
        print(f"Received from server: {response}")

    client_sock.close()

