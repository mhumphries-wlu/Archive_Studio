import os
import sys
import argparse
from process_boxes import test_process_image

def main():
    parser = argparse.ArgumentParser(description='Test bounding box functionality with Gemini API')
    parser.add_argument('--image', '-i', required=True, help='Path to image file')
    parser.add_argument('--text', '-t', help='Text to process (if not provided, will be taken from a text file with same name as image)')
    parser.add_argument('--api_key', '-k', help='Google API key (if not provided, will use GOOGLE_API_KEY environment variable)')
    
    args = parser.parse_args()
    
    # Check if image exists
    if not os.path.exists(args.image):
        print(f"ERROR: Image file not found: {args.image}")
        return 1
        
    # Get text from file if not provided
    if not args.text:
        text_file = os.path.splitext(args.image)[0] + '.txt'
        if os.path.exists(text_file):
            with open(text_file, 'r', encoding='utf-8') as f:
                args.text = f.read()
            print(f"Loaded text from {text_file}")
        else:
            print(f"ERROR: No text provided and couldn't find text file {text_file}")
            return 1
    
    # Set API key
    if args.api_key:
        os.environ['GOOGLE_API_KEY'] = args.api_key
    elif 'GOOGLE_API_KEY' not in os.environ:
        print("ERROR: No Google API key provided. Use --api_key or set GOOGLE_API_KEY environment variable")
        return 1
        
    # Run the test
    test_process_image(args.image, args.text)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 