import logging, os, argparse, sys, re, yaml, importlib
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG: object = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

file_handler: object = RotatingFileHandler("log/cli.log", maxBytes=5*1024*1024, backupCount=5)
stream_handler: object = logging.StreamHandler()

formatter: object = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

LOG.addHandler(file_handler)
LOG.addHandler(stream_handler)

CONFIG_LS: list = [
    "settings"
] # will be used when fetch_config is called and will load all yaml config listed
args: object = None

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

def verify_input() -> None:
    if os.environ.get("MODE", "NULL") == "NULL":
        LOG.error("*** No mode was set ***")
        sys.exit()

    condition: bool = os.environ.get("MODE", "NULL") == "file" and not os.environ.get("FILEPATH", "NULL")
    if condition and (not os.path.exists(os.environ.get("FILEPATH", "NULL")) or not os.environ.get("FILEPATH", "NULL").endswith(".txt")):
        LOG.error("*** Type of file path is invalid ***")
        sys.exit()
    LOG.info("---> Passed verification check")

# Used only for when we read a file
def remove_literals(line: str) -> str:
    line = re.sub(r'["\'].*?["\']', '', line)
    line = re.sub(r'\b\d+(\.\d+)?\b', '', line)
    line = re.sub(r'[^\w\s]', '', line)
    return line.strip()


def read_input() -> list:
    text: list = None

    match os.environ.get("MODE", "NULL"):
        case "file":
            LOG.info("---> File mode was set")
            
            with open(os.environ.get("FILEPATH", "NULL"), "r") as f:
                dirty_text = f.readlines()
            
            text = [remove_literals(t) for t in dirty_text]
            LOG.info("---> File read")
            LOG.debug(text)
        case "cli":
            LOG.info("---> CLI mode was set")
            LOG.info("---> Listening to user input")
            print("==== Listening User Input ====")
            text = [input("Your Input: ")]
            LOG.debug(f"---> User input : {text}")
        case _:
            LOG.error("*** Not valid input for mode ***")
            sys.exit()

    LOG.info("---> Finished extraction")
    return text

def saved_input(results: list) -> None:
    LOG.info("---> Saved result to result.yaml")
    with open("result.yaml", "w") as f:
        yaml.dump({"date": datetime.now(), "result": results}, f, default_flow_style=False)

if __name__ == '__main__':
    parser: object = argparse.ArgumentParser(description="Input where text would be retrieve.")
    parser.add_argument("--input", type=str, required=True, help="File or cli based input")
    parser.add_argument("--path", type=str, help="File path where text is located")

    args = parser.parse_args()
    
    # gloablizing because preference ko 
    os.environ["MODE"] = args.input
    if args.path != None:
        os.environ["FILEPATH"] = args.path

    LOG.info("==== Verification of Parameters ====")
    verify_input()

    LOG.info("==== Begin Extraction ====")
    text_inp: str|list = read_input() 

    LOG.info("==== Loading Model ====")
    # We will load the module that is refered inside yaml settings
    conf: dict = fetch_config()
    model_module: object =  importlib.import_module(f"model.{conf['settings']['modelName']}") # this will be used to use the model
    LOG.info("---> Successful import of model")
    
    # Initialize class name from modelType
    model_name: str = conf["settings"]["modelType"]
    model_cls: object = getattr(model_module, model_name)
    model_inst: object = model_cls()
    LOG.info("---> Finalized initialization of model")
    
    LOG.info("==== Fitting the Text to Model ====")
    results: list = []
    for text in text_inp:
        result: list = model_inst.fit(text)
        results.append(result)
        print("Species with Allergens and Sentiment (with positions):")
        for item in result:
            species_name, allergen, sentiment, species_start_idx, species_end_idx, allergen_start, allergen_end = item
            print(f"Species: {species_name}, Allergen: {allergen}, Sentiment: {sentiment}, "
                  f"Species position: ({species_start_idx}, {species_end_idx}), "
                  f"Allergen position: ({allergen_start}, {allergen_end})")

    save_input(results)
