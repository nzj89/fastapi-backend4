from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
import random
import traceback
from colorama import Fore, Style
import socket
import os

app = FastAPI()

# Hardcoded Prompt
hardcoded_prompt = (
    "Hi AI, we're providing a list of properties with descriptions. Each line typically represents a specific detail about the property. For instance:\n\n"
    "21\n"
    "EXCLUSIVITÉ\n"
    "Maison 6 pièces 250 m²\n"
    "53110 Lassay-les-Châteaux\n"
    "399 000 €\n"
    "1 596 €/m²\n\n"
    "In this case, the property has 21 pictures. Please rank the list from the best to worst deal, taking into account all relevant factors such as price, size, number of rooms, and additional details. Do not rely solely on price per square meter. "
    "Provide a clear and concise explanation for your ranking. The explanation should be easy to understand, highlighting the pros and cons of each property.\n\n"
    "Add a final extensive thought with all your knowledge about real estate, particularly in the context of Lassay-les-Châteaux. Discuss whether these properties are worth considering or if there are better buys elsewhere. Provide as much extra value in your reply as you can to impress the user.\n\n"
    "This is super important: Format your reply using HTML tags to ensure it looks clean and is easy to stylize on the frontend. For example:\n"
    "<h2>Ranked Property List</h2>\n<p>some text</p>\n"
    "<h3>4. Maison 6 pièces 100m² - 658€/m²</h3> instead of <h3>Maison 6 pièces 100m² - 658€/m²</h3>\n\n"
    "Here is an example of the expected HTML structure:\n"
    "<h2>Ranked List of Properties</h2>\n"
    "<h3>1. Maison 8 pièces 140 m² - €2,329/m² (27 pictures)</h3>\n"
    "<ul>\n"
    "  <li>8 rooms offer great value</li>\n"
    "  <li>Pricey, but may be worth it for the size</li>\n"
    "</ul>\n"
    "<h3>2. Maison 6 pièces 140 m² - €2,250/m² (17 pictures)</h3>\n"
    "<ul>\n"
    "  <li>Comparable to the previous property in terms of size and price</li>\n"
    "</ul>\n\n"
    "Ensure each property is listed with a header that includes the rank, property type, size, price per square meter, and number of pictures. Provide additional insights in a list format below each property header.\n\n"
    "Additionally, conclude with an overall assessment and additional insights formatted as follows:\n"
    "<h2>Overall Assessment</h2>\n<p>Your detailed assessment text here</p>\n"
    "<h2>Additional Insights</h2>\n<p>Additional insights text here</p>\n\n"
    "Now, rank the following list and provide your formatted HTML response:"
)
chat_prompt_format = (
    "Hi AI, please respond to the following message. Format your reply using HTML tags to ensure it looks clean and is easy to stylize on the frontend. "
    "For example:\n"
    "<h2>Relevant Title to the prompt </h2>\n<p>some text</p>\n\n"
    "Here is an example of the expected HTML structure:\n"
    "<h2>Another needed title just in case</h2>\n"
    "<p>This is an example response</p>\n\n"
    "Now, please respond to the following message in a similar HTML formatted structure:\n\n"
)

# Retrieve host IP address upon FastAPI startup
fastApiHost_ip = socket.gethostbyname(socket.gethostname())
print("FastAPI Host IP:", fastApiHost_ip)

origins = ["http://localhost:8080", "http://192.168.1.21:8080", "https://main--nzrealstate.netlify.app", "https://nzrealstate.netlify.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Function to send requests to OpenAI
def send_to_openai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.9,
            top_p=1,
            n=1,
            stop=None
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error sending request to OpenAI: {str(e)}")
        return ""

@app.post('/generate-story')
async def generate_story(request: Request):
    try:
        data = await request.json()
        user_prompt = data.get('prompt')
        print(f'Received request to generate story with prompt: {user_prompt}')

        # Concatenate chat_prompt_format with the user's prompt
        formatted_prompt = chat_prompt_format + user_prompt
        print(f'Formatted prompt: {formatted_prompt}')

        generated_text = send_to_openai(formatted_prompt)
        print(f'Generated Story: {generated_text}')

        return {"generated_story": generated_text}
    except Exception as e:
        print(f'Error generating story: {str(e)}')
        return {"error": str(e)}

@app.post('/rank-properties')
async def rank_properties(request: Request):
    try:
        data = await request.json()
        properties_list = data.get('propertiesList')
        print(f'{Fore.GREEN}Rank Properties: properties_list -> {Style.RESET_ALL}{properties_list}')

        # Concatenate the properties list with the hardcoded prompt
        prompt = hardcoded_prompt + "\n\n" + "\n".join(properties_list)
        print(f'{Fore.CYAN}AI prompt {Style.RESET_ALL}{prompt}')
        # Call AI to rank properties
        ranked_properties = send_to_openai(prompt)
        print(f'{Fore.CYAN}AI Response after prompt {Style.RESET_ALL}{ranked_properties}')

        return {"rankedProperties": ranked_properties, "error": None}
    except Exception as e:
        print(f'Error ranking properties: {str(e)}')
        return {"rankedProperties": None, "error": str(e)}

# Scrape reviews function with headless Chrome
def scrape_reviews_async(url):
    print(' ** Welcome to scrape_reviews_async')
    try:
        # Set the user agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        # Initialize ChromeOptions
        chrome_options = Options()
        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.add_argument("--headless")  # Run Chrome in headless mode
        chrome_options.add_argument("--no-sandbox")  # Required for running as root in some environments
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        chrome_options.add_argument("--disable-gpu")  # Disable GPU usage if not needed
        chrome_options.add_argument("--window-size=1920x1080")  # Set the window size if necessary

        # Initialize a Selenium WebDriver (you may need to provide the path to your WebDriver executable)
        driver = webdriver.Chrome(options=chrome_options)
        # Call your function or logic here
        print(f"we are opening the url {url}")
        driver.get(url)
        print(f"Page Title: {driver.title}")

        if "www.ouestfrance-immo.com" in url:
            # Wait for the DOM to load
            element = driver.find_element("annLink")
            print(f"Content of the element with class 'annLink': {element.text}")

        elif "www.bienici.com" in url:

            cookies_button = driver.find_element(By.ID, "didomi-notice-agree-button")
            print("cookies_button found")
            wait = WebDriverWait(driver, timeout=2)
            wait.until(lambda d : cookies_button.is_displayed())
            print("cookies_button displayed")
            cookies_button.click()
            print("cookies_button was clicked")

            # Wait for the DOM to load
            elements = driver.find_elements(By.CLASS_NAME, "sideListInside")

            # Print the size of the list
            print(f"Number of elements with class 'sideListInside': {len(elements)}")

            scraped_data = []

            # Print content of all elements with class 'sideListInside'
            for index, element in enumerate(elements, 1):
                print(f"\nContent of element {Fore.GREEN} {index} {Style.RESET_ALL} with class 'sideListInside':\n{Fore.CYAN}{element.text}{Style.RESET_ALL}")

                try:
                    image = element.find_element(By.CLASS_NAME, "img__image--fit-to-parent")
                    image_url = image.get_attribute('src')
                except Exception as e:
                    print(f"Error finding image for element {index}: {e}")
                    image_url = "No image available"

                property_details = element.text
                combined_entry = f"{image_url}\n{property_details}"
                scraped_data.append(combined_entry)
                print(f"\nCombined entry {Fore.GREEN} {index + 1} {Style.RESET_ALL}:\n{Fore.CYAN}{combined_entry}{Style.RESET_ALL}")

                print(f"\nscraped_data {Fore.BLUE} {scraped_data} {Style.RESET_ALL}")

        driver.quit()
        print("Scraping completed successfully")
        return scraped_data

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

# Add this route to your FastAPI application
@app.post("/add-ip")
def add_ip(ip: str):
    print(f"Received request to add IP: {ip}")
    if ip in origins:
        print(f"IP {ip} already exists in the origins list. Origins: {origins}")
        return {"message": f"IP {ip} already exists.", "origins": origins, "fastApiHostIp": fastApiHost_ip}
    else:
        origins.append(ip)
        print(f"IP {ip} added to the origins list.")
        print(f"Updated origins list: {origins}")
        return {"message": f"IP {ip} added successfully.", "origins": origins, "fastApiHostIp": fastApiHost_ip}

# Endpoint to return the list of allowed origins
@app.get("/allowed-origins")
def get_allowed_origins():
    return {"allowed_origins": origins}

@app.get("/current-ip")
def read_current_ip():
    return {"ip": socket.gethostbyname(socket.gethostname())}

@app.post('/process-url')
async def process_url(request: Request):
    print("The backend received your request, we will run process-url")
    try:
        data = await request.json()
        url = data.get('url')
        print(f'================== Received URL from frontend: {url}, we will run scrape_reviews_async')

        # Call your function or logic here
        result = scrape_reviews_async(url)

        return {"listingsArrayFromBackend": result, "error": None}
    except Exception as e:
        print(f'Error processing URL: {str(e)}')
        return {"listingsArrayFromBackend": None, "error": str(e)}

@app.get('/')
def hello():
    print("Received request at /")
    return {"message": 'Hello from FastAPI! Have a nice day!'}

@app.post('/random-number')
def random_number():
    generated_number = random.randint(1, 100)
    print(f'Received request at /random-number. Generated Number: {generated_number}')
    return generated_number

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

