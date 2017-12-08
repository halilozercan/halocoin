import React, { Component } from 'react';

class MAlert extends Component {
  render() {
    return (
      <div class={"alert alert-" + this.props.type}>
        <div class="container-fluid">
          <div class="alert-icon">
        	 <i class="material-icons">{this.props.icon}</i>
          </div>
          {this.props.text}
        </div>
      </div>
    );
  }
}

export default MAlert;
