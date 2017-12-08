import React, { Component } from 'react';

class MButton extends Component {
  render() {
    return (
      <button className={'btn btn-' + this.props.type}>{this.props.text}</button>
    );
  }
}

export default MButton;
