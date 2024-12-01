import logging, os, argparse, sys, re, yaml, importlib, socket
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG: object = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

file_handler: object = RotatingFileHandler("log/server.log", maxBytes=5*1024*1024, backupCount=5)
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


def saved_input(results: list) -> None:
    LOG.info("---> Saved result to result.yaml")
    with open("result.yaml", "w") as f:
        yaml.dump({"date": datetime.now(), "result": results}, f, default_flow_style=False)

if __name__ == '__main__':
    LOG.info("==== Booting Server ====")
    conf: dict = fetch_config()
    host: str = conf["settings"]["ip"]
    port: int = int(conf["settings"]["port"])

    server_sock: object = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((host, port))
    LOG.debug(f"---> Host a server on {host}:{port}")

    LOG.info("==== Loading Model ====")
    # We will load the module that is refered inside yaml settings
    model_module: object =  importlib.import_module(f"model.{conf['settings']['modelName']}") # this will be used to use the model
    LOG.info("---> Successful import of model")
    
    # Initialize class name from modelType
    model_name: str = conf["settings"]["modelType"]
    model_cls: object = getattr(model_module, model_name)
    model_inst: object = model_cls()
    LOG.info("---> Finalized initialization of model")

    LOG.info("==== Running Server ====")
    server_sock.listen(1)
    is_running: bool = True
    while is_running:
        client_sock, client_addr = server_sock.accept()
        LOG.debug(f"---> Client connected {client_addr}")

        try: 
            while True:  # Allow multiple messages per client session
                text: str = client_sock.recv(1024).decode("utf-8")
                if not text:  # Client disconnected or sent an empty string
                    LOG.debug(f"Client {client_addr} disconnected.")
                    break

                LOG.debug(f"---> Client text: {text}")
                
                LOG.info("==== Fitting the Text to Model ====")
                try:
                    result: list = model_inst.fit(text)
                    for item in result:
                        species_name, allergen, sentiment, species_start_idx, species_end_idx, allergen_start, allergen_end = item
                        LOG.debug(f"Species: {species_name}, Allergen: {allergen}, Sentiment: {sentiment}, "
                                  f"Species position: ({species_start_idx}, {species_end_idx}), "
                                  f"Allergen position: ({allergen_start}, {allergen_end})")

                    response: str = str(result)
                    LOG.info("---> Sending a response")
                    client_sock.send(response.encode("utf-8"))
                    LOG.info("---> Packet sent to client")
                except Exception as model_error:
                    LOG.error(f"---> Model processing error: {model_error}")

        except Exception as comm_error:
            LOG.error(f"---> Communication error with {client_addr}: {comm_error}")
        finally:
            client_sock.close()
            LOG.debug(f"---> Connection with {client_addr} closed.")
