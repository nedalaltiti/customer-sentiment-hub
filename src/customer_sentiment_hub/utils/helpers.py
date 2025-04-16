"""Helper functions."""

import json
import os
from typing import Any, Dict, List, Tuple, Union


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dict[str, Any]: The loaded JSON data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: Dict[str, Any], file_path: str) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: The data to save
        file_path: Path to the output file
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def extract_review_texts(data: Union[List, Dict]) -> List[str]:
    """
    Extract review texts from various data structures.
    
    Args:
        data: Input data containing reviews
        
    Returns:
        List[str]: Extracted review texts
    """
    review_texts = []
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                review_texts.append(item)
            elif isinstance(item, dict) and 'text' in item:
                review_texts.append(item['text'])
    elif isinstance(data, dict):
        if 'reviews' in data and isinstance(data['reviews'], list):
            for review in data['reviews']:
                if isinstance(review, dict) and 'text' in review:
                    review_texts.append(review['text'])
        else:
            for key, value in data.items():
                if isinstance(value, str):
                    review_texts.append(value)
    
    return review_texts


def batch_items(items: List[Any], batch_size: int) -> List[List[Any]]:
    """
    Split a list into batches.
    
    Args:
        items: The list to split
        batch_size: Size of each batch
        
    Returns:
        List[List[Any]]: List of batches
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]