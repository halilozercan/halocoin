import React, { Component } from 'react';
import {MCardStats, MCardTable} from '../components/card.js';
import { Alert, AlertList } from "react-bs-notifier";

class Address extends Component {

  constructor(props) {
    super(props);
    this.copyToClipboard = this.copyToClipboard.bind(this);
  }

  copyToClipboard() {
    var textField = document.createElement('textarea');
    textField.innerText = this.props.address;
    document.body.appendChild(textField);
    textField.select();
    document.execCommand('copy');
    textField.remove();
  }

  render() {
    return (
      <div className="col-lg-3 col-md-6 col-sm-6" onClick={this.copyToClipboard}>
        <MCardStats color="red" header_icon="info_outline" title="Address"
         content={this.props.address.substring(0,8) + '...'}
         footer_icon="local_offer" alt_text={"Belongs to: " + this.props.name}/>
      </div>
    );
  }
}

export default Address;