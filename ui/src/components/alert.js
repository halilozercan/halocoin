import React, { Component } from 'react';

class MAlert extends Component {
  render() {
    return (
      <div className={"alert alert-" + this.props.type}>
        <div className="container-fluid">
          <div className="alert-icon">
        	 <i className="material-icons">{this.props.icon}</i>
          </div>
          {this.props.text}
          {this.props.children}
        </div>
      </div>
    );
  }
}

export default MAlert;
