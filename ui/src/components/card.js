
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

class CardRow extends Component {
  render() {
    return(
      <tr key={this.props.index}>
        {Object.values(this.props.row).map((col, j) => {
          return <td key={j}>{col}</td>;
        }
        )}
      </tr>
    );
  }
}

class MCardTable extends Component {
  render() {
    if(this.props.rows !== null) {
      let data = <a style={{"textAlign":"center"}}>We could not find any data to fill this table :(</a>;
      if(this.props.rows.length > 0) {
        data = this.props.rows.map((_row, i) => {
                return <CardRow key={i} row={_row} index={i}/>;
              });
      }
      return (
        <div className="card">
          <div className="card-header" data-background-color={this.props.color}>
              <h4 className="title">{this.props.title}</h4>
              <p className="category">{this.props.description}</p>
          </div>
          <div className="card-content table-responsive">
            <table className="table table-hover" style={{"fontFamily": "monospace"}}>
              <thead className="text-warning">
                <tr>
                  {Object.values(this.props.columns).map((name, index) => {
                    return <th key={ index }>{name}</th>;
                  })}
                </tr>
              </thead>
              <tbody>
                {data}
              </tbody>
            </table>
          </div>
        </div>
      );
    } else {
      return (
        <div className="card">
          <div className="card-header" data-background-color={this.props.color}>
              <h4 className="title">{this.props.title}</h4>
              <p className="category">{this.props.description}</p>
          </div>
          <div className="card-content">
            Loading
          </div>
        </div>
      );
    }
  }
}

export {MCardStats, MCardTable};
