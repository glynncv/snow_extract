"""
Data Export Utilities
=====================

Handles exporting incident data and analysis results to various formats.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


def export_to_csv(
    data: Union[pd.DataFrame, List[pd.DataFrame]],
    output_path: Union[str, Path],
    **kwargs
) -> Path:
    """
    Export DataFrame(s) to CSV format.

    Args:
        data: Single DataFrame or list of DataFrames to export
        output_path: Output file path (for single DF) or directory (for multiple DFs)
        **kwargs: Additional arguments passed to pd.DataFrame.to_csv()

    Returns:
        Path: Path to exported file or directory

    Examples:
        >>> df = pd.DataFrame({'a': [1, 2, 3]})
        >>> export_to_csv(df, 'output/data.csv')

        >>> dfs = [df1, df2, df3]
        >>> export_to_csv(dfs, 'output/', index=False)
    """
    output_path = Path(output_path)

    # Default: no index
    kwargs.setdefault('index', False)

    if isinstance(data, pd.DataFrame):
        # Single DataFrame export
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(output_path, **kwargs)
        logger.info(f"Exported {len(data)} records to {output_path}")
        return output_path

    elif isinstance(data, list):
        # Multiple DataFrames - create directory
        output_path.mkdir(parents=True, exist_ok=True)

        for i, df in enumerate(data):
            file_path = output_path / f"data_{i+1}.csv"
            df.to_csv(file_path, **kwargs)
            logger.info(f"Exported sheet {i+1}: {len(df)} records to {file_path}")

        return output_path

    else:
        raise TypeError(f"data must be DataFrame or list of DataFrames, got {type(data)}")


def export_to_excel(
    data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
    output_path: Union[str, Path],
    sheet_name: str = "Sheet1",
    include_index: bool = False,
    **kwargs
) -> Path:
    """
    Export DataFrame(s) to Excel format.

    Args:
        data: Single DataFrame or dict of {sheet_name: DataFrame}
        output_path: Output Excel file path (.xlsx)
        sheet_name: Sheet name (used only for single DataFrame)
        include_index: Whether to include DataFrame index
        **kwargs: Additional arguments passed to pd.ExcelWriter()

    Returns:
        Path: Path to exported Excel file

    Examples:
        >>> df = pd.DataFrame({'a': [1, 2, 3]})
        >>> export_to_excel(df, 'output/data.xlsx')

        >>> sheets = {'SLA': sla_df, 'Backlog': backlog_df}
        >>> export_to_excel(sheets, 'output/report.xlsx')
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure .xlsx extension
    if output_path.suffix != '.xlsx':
        output_path = output_path.with_suffix('.xlsx')

    try:
        with pd.ExcelWriter(output_path, engine='openpyxl', **kwargs) as writer:
            if isinstance(data, pd.DataFrame):
                # Single sheet
                data.to_excel(writer, sheet_name=sheet_name, index=include_index)
                logger.info(f"Exported {len(data)} records to {output_path} (sheet: {sheet_name})")

            elif isinstance(data, dict):
                # Multiple sheets
                for name, df in data.items():
                    df.to_excel(writer, sheet_name=name, index=include_index)
                    logger.info(f"Exported sheet '{name}': {len(df)} records")

            else:
                raise TypeError(f"data must be DataFrame or dict of DataFrames, got {type(data)}")

    except ImportError:
        logger.error("openpyxl not installed. Install with: pip install openpyxl")
        raise

    return output_path


def export_to_json(
    data: Union[pd.DataFrame, Dict[str, Any]],
    output_path: Union[str, Path],
    orient: str = 'records',
    indent: int = 2,
    **kwargs
) -> Path:
    """
    Export DataFrame or dict to JSON format.

    Args:
        data: DataFrame or dictionary to export
        output_path: Output JSON file path
        orient: JSON orientation for DataFrames ('records', 'index', 'columns', 'values')
        indent: JSON indentation for readability
        **kwargs: Additional arguments passed to json.dump() or DataFrame.to_json()

    Returns:
        Path: Path to exported JSON file

    Examples:
        >>> df = pd.DataFrame({'a': [1, 2, 3]})
        >>> export_to_json(df, 'output/data.json')

        >>> metrics = {'sla_breach_rate': 5.2, 'total_incidents': 100}
        >>> export_to_json(metrics, 'output/metrics.json')
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure .json extension
    if output_path.suffix != '.json':
        output_path = output_path.with_suffix('.json')

    if isinstance(data, pd.DataFrame):
        # DataFrame to JSON
        data.to_json(output_path, orient=orient, indent=indent, **kwargs)
        logger.info(f"Exported {len(data)} records to {output_path}")

    elif isinstance(data, dict):
        # Dict to JSON
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=indent, **kwargs)
        logger.info(f"Exported dictionary to {output_path}")

    else:
        raise TypeError(f"data must be DataFrame or dict, got {type(data)}")

    return output_path


def export_metrics(
    metrics: Dict[str, Any],
    output_path: Union[str, Path],
    format: str = 'json'
) -> Path:
    """
    Export metrics dictionary to file.

    Convenience wrapper for exporting analysis metrics.

    Args:
        metrics: Dictionary of metrics (e.g., from calculate_sla_metrics())
        output_path: Output file path
        format: Export format ('json' or 'csv')

    Returns:
        Path: Path to exported file

    Examples:
        >>> metrics = calculate_sla_metrics(df)
        >>> export_metrics(metrics, 'output/sla_metrics.json')
    """
    if format.lower() == 'json':
        return export_to_json(metrics, output_path)
    elif format.lower() == 'csv':
        # Convert dict to single-row DataFrame
        df = pd.DataFrame([metrics])
        return export_to_csv(df, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'")
