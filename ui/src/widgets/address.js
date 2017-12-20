import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';

class Address extends Component {

  copyToClipboard = () => {
    var textField = document.createElement('textarea');
    textField.innerText = this.props.address;
    document.body.appendChild(textField);
    textField.select();
    document.execCommand('copy');
    textField.remove();
    this.props.notify('Address is copied to clipboard', 'info', 'tc');
  }

  render() {
    if(this.props.wallet !== null) {
      console.log('not null');
      return (
        <div className="col-lg-6 col-md-12 col-sm-12" onClick={this.copyToClipboard}>
          <MCardStats color="red" header_icon="info_outline" title="Address"
           content={this.props.wallet.address.substring(0,8) + '...'}
           footer_icon="local_offer" alt_text={"Belongs to: " + this.props.wallet.name}/>
        </div>
      );
    }
    else {
      console.log(' null');
      return <div />;
    }
  }
}

export default Address;