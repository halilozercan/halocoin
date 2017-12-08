
import React, { Component } from 'react';

class MCardStats extends Component {
  render() {
    return (
      <div className="card card-stats">
        <div className="card-header" data-background-color={this.props.color}>
          <i className="material-icons">{this.props.header_icon}</i>
        </div>
        <div className="card-content">
          <p className="category">{this.props.title}</p>
          <h3 className="title">{this.props.content}</h3>
        </div>
        <div className="card-footer">
          <div className="stats">
            <i className="material-icons">{this.props.footer_icon}</i> {this.props.alt_text}
          </div>
        </div>
      </div>
    );
  }
}

class MCardTable extends Component {
  render() {

    return (
      <div className="card">
        <div className="card-header" data-background-color={this.props.color}>
            <h4 className="title">{this.props.title}</h4>
            <p className="category">{this.props.description}</p>
        </div>
        <div className="card-content table-responsive">
          <table className="table table-hover">
            <thead className="text-warning">
              {this.props.columns.map((name, index) => {
                <th key={ index }>{name}</th>
              })}
            </thead>
            <tbody>
              {this.props.rows.forEach((row, i) =>
                <tr key={i}>
                  {Object.keys(row).map((col, j) =>
                    <td key={j}>{col}</td>
                  )}
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
}

export {MCardStats, MCardTable};
